#!/usr/bin/env python3
"""
Fetch aurora observation data from multiple sources and compile into JSON.
"""

import argparse
from datetime import datetime, timezone, timedelta
import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse

# Finnish time (EET = UTC+2, no DST in February)
FINNISH_TZ = timezone(timedelta(hours=2))

# API endpoints (location-independent)
OVATION_URL = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
KP_FORECAST_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
SOLAR_WIND_URL = "https://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json"

# User agent for MET Norway API (required)
USER_AGENT = "OuluAuroraTracker/1.0 (https://github.com/bennokress/Oulu-Aurora)"


def fetch_json(url: str) -> dict | list | None:
    """Fetch JSON data from a URL."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"Error fetching {url}: {e}")
        return None


def fetch_cloud_coverage(lat: float, lon: float) -> float | None:
    """Fetch cloud coverage percentage from MET Norway."""
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    data = fetch_json(url)
    if data is None:
        return None

    try:
        # Get the first timeseries entry (current/nearest forecast)
        timeseries = data.get("properties", {}).get("timeseries", [])
        if timeseries:
            instant_data = timeseries[0].get("data", {}).get("instant", {}).get("details", {})
            cloud_coverage = instant_data.get("cloud_area_fraction")
            return float(cloud_coverage) if cloud_coverage is not None else None
    except Exception as e:
        print(f"Error parsing cloud coverage: {e}")
    return None


def fetch_ovation_data(lat: float, lon: float) -> tuple[float | None, float | None]:
    """
    Fetch aurora probability from NOAA Ovation data.
    Returns (point_probability, regional_average).
    """
    data = fetch_json(OVATION_URL)
    if data is None:
        return None, None

    try:
        coordinates = data.get("coordinates", [])

        # Round to nearest integer for OVATION grid matching
        target_lat = round(lat)
        target_lon = round(lon)

        # Region boundaries (±1 degree around target)
        region_lat_min = target_lat - 1
        region_lat_max = target_lat + 1
        region_lon_min = target_lon - 1
        region_lon_max = target_lon + 1

        point_probability = None
        regional_values = []

        for coord in coordinates:
            coord_lon = coord[0]
            coord_lat = coord[1]
            aurora = coord[2]

            # Find exact point (OVATION uses integer coordinates)
            if coord_lat == target_lat and coord_lon == target_lon:
                point_probability = float(aurora)

            # Collect regional values
            if (region_lon_min <= coord_lon <= region_lon_max and
                region_lat_min <= coord_lat <= region_lat_max):
                regional_values.append(float(aurora))

        regional_avg = None
        if regional_values:
            regional_avg = round(sum(regional_values) / len(regional_values), 1)

        return point_probability, regional_avg
    except Exception as e:
        print(f"Error parsing Ovation data: {e}")
    return None, None


def fetch_kp_indices() -> tuple[float | None, float | None, float | None]:
    """
    Fetch KP indices from NOAA.
    Returns (current, 3h_forecast, 6h_forecast).

    Uses timestamp-based approach: finds the latest observed entry,
    then takes the next two entries as 3h and 6h forecasts.
    """
    data = fetch_json(KP_FORECAST_URL)
    if data is None:
        return None, None, None

    try:
        # Data format: [["time_tag", "Kp", "observed", "noaa_scale"], ...]
        # First row is header, subsequent rows are data sorted by time
        rows = data[1:]  # Skip header

        # Find the index of the last observed entry
        last_observed_idx = None
        for i, row in enumerate(rows):
            if len(row) >= 3 and row[2] == "observed":
                last_observed_idx = i

        if last_observed_idx is None:
            return None, None, None

        # Current KP is the last observed value
        current_kp = float(rows[last_observed_idx][1])

        # 3h and 6h forecasts are the next two entries after the last observed
        kp_3h = None
        kp_6h = None

        if last_observed_idx + 1 < len(rows):
            kp_3h = float(rows[last_observed_idx + 1][1])
        if last_observed_idx + 2 < len(rows):
            kp_6h = float(rows[last_observed_idx + 2][1])

        return current_kp, kp_3h, kp_6h
    except Exception as e:
        print(f"Error parsing KP indices: {e}")
    return None, None, None


def fetch_solar_wind() -> tuple[float | None, float | None]:
    """
    Fetch Bz and Bt values from NOAA solar wind data.
    Returns (bz, bt).
    """
    data = fetch_json(SOLAR_WIND_URL)
    if data is None:
        return None, None

    try:
        bz = data.get("Bz")
        bt = data.get("Bt")

        # Convert to float if present
        bz = float(bz) if bz is not None else None
        bt = float(bt) if bt is not None else None

        return bz, bt
    except Exception as e:
        print(f"Error parsing solar wind data: {e}")
    return None, None


def calculate_aurora_indicator(aurora_probability: float | None,
                                clouds: float | None) -> float:
    """
    Calculate aurora visibility indicator (0-100).

    Based on NOAA OVATION aurora probability with cloud visibility penalty.
    - 0-50% clouds: no penalty (full visibility assumed)
    - 50-100% clouds: linear penalty down to 0% at full cloud cover

    Note: OVATION data is purely space weather - it does NOT account for
    cloud coverage, so we apply our own visibility adjustment.
    """
    if aurora_probability is None:
        return 0.0

    # Calculate visibility multiplier based on cloud coverage
    if clouds is None or clouds <= 50:
        visibility = 1.0
    else:
        # Linear scale from 1.0 at 50% clouds to 0.0 at 100% clouds
        visibility = (100 - clouds) / 50

    indicator = aurora_probability * visibility
    return round(max(0, min(100, indicator)), 1)


def calculate_traffic_light(aurora_indicator: float) -> str:
    """
    Calculate traffic light indicator based on aurora indicator score.

    Returns color based on aurora viewing conditions:
    - red: Go outside now - excellent chance of visible aurora
    - yellow: Worth checking - moderate chance
    - green: Possible but unlikely - low chance
    - black: Don't bother - very low chance or not visible
    """
    if aurora_indicator >= 50:
        return "red"  # Go outside now!
    elif aurora_indicator >= 25:
        return "yellow"  # Worth checking
    elif aurora_indicator >= 10:
        return "green"  # Maybe
    else:
        return "black"  # Don't bother


def generate_badge(label: str, message: str, color: str) -> dict:
    """Generate a shields.io endpoint badge JSON object."""
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color
    }


def get_recommendation_badge(traffic_light: str) -> dict:
    """Generate recommendation badge based on traffic light."""
    messages = {
        "red": "Pretty sure",
        "yellow": "Worth checking",
        "green": "Probably not",
        "black": "Definitely not"
    }
    return generate_badge(
        "Current Status",
        messages.get(traffic_light, "Unknown"),
        traffic_light if traffic_light != "black" else "gray"
    )


def get_aurora_probability_badge(probability: float | None) -> dict:
    """Generate aurora probability badge with traffic light colors."""
    if probability is None:
        return generate_badge("Aurora Probability", "N/A", "gray")

    if probability >= 50:
        color = "red"
    elif probability >= 25:
        color = "yellow"
    elif probability >= 10:
        color = "green"
    else:
        color = "gray"

    return generate_badge("Aurora Probability", f"{probability:.0f}%", color)


def get_cloud_coverage_badge(clouds: float | None) -> dict:
    """Generate cloud coverage badge (inverted - low clouds = good = red)."""
    if clouds is None:
        return generate_badge("Cloud Coverage", "N/A", "gray")

    # Inverted logic: clear skies (low clouds) = red (good)
    if clouds <= 25:
        color = "red"
    elif clouds <= 50:
        color = "yellow"
    elif clouds <= 75:
        color = "green"
    else:
        color = "gray"

    return generate_badge("Cloud Coverage", f"{clouds:.0f}%", color)


def get_kp_index_badge(kp: float | None) -> dict:
    """Generate KP index badge with traffic light colors."""
    if kp is None:
        return generate_badge("KP Index", "N/A", "gray")

    if kp >= 5:
        color = "red"
    elif kp >= 3:
        color = "yellow"
    elif kp >= 2:
        color = "green"
    else:
        color = "gray"

    return generate_badge("KP Index", f"{kp:.1f}", color)


def get_bz_badge(bz: float | None) -> dict:
    """Generate Bz badge (negative = good = red)."""
    if bz is None:
        return generate_badge("Bz", "N/A", "gray")

    # Negative Bz is good for aurora
    if bz <= -10:
        color = "red"
    elif bz <= -5:
        color = "yellow"
    elif bz < 0:
        color = "green"
    else:
        color = "gray"

    return generate_badge("Bz", f"{bz:.1f} nT", color)


def get_bt_badge(bt: float | None) -> dict:
    """Generate Bt badge (higher = better = red)."""
    if bt is None:
        return generate_badge("Bt", "N/A", "gray")

    if bt >= 20:
        color = "red"
    elif bt >= 10:
        color = "yellow"
    elif bt >= 5:
        color = "green"
    else:
        color = "gray"

    return generate_badge("Bt", f"{bt:.1f} nT", color)


def write_badges(traffic_light: str, aurora_prob: float | None,
                 clouds: float | None, kp: float | None,
                 bz: float | None, bt: float | None) -> None:
    """Write all badge JSON files."""
    os.makedirs("badges", exist_ok=True)

    badges = {
        "recommendation": get_recommendation_badge(traffic_light),
        "aurora-probability": get_aurora_probability_badge(aurora_prob),
        "cloud-coverage": get_cloud_coverage_badge(clouds),
        "kp-index": get_kp_index_badge(kp),
        "bz": get_bz_badge(bz),
        "bt": get_bt_badge(bt)
    }

    for name, badge in badges.items():
        with open(f"badges/{name}.json", "w") as f:
            json.dump(badge, f, indent=2)


def send_pushover_notification(location_name: str, indicator: float,
                                aurora_prob: float | None,
                                clouds: float | None, traffic_light: str,
                                notify_start: datetime | None = None,
                                notify_end: datetime | None = None) -> bool:
    """
    Send a push notification via Pushover.

    Only sends if:
    - Running on GitHub Actions (GITHUB_ACTIONS env var is set)
    - PUSHOVER_TOKEN and PUSHOVER_USER env vars are configured
    - Traffic light is yellow or better
    - Current time is within notification window (if specified)

    Returns True if notification was sent successfully.
    """
    # Only send notifications when running on GitHub Actions
    if not os.environ.get("GITHUB_ACTIONS"):
        print("  Skipping Pushover notification (not running on GitHub Actions)")
        return False

    pushover_token = os.environ.get("PUSHOVER_TOKEN")
    pushover_user = os.environ.get("PUSHOVER_USER")

    if not pushover_token or not pushover_user:
        print("  Skipping Pushover notification (credentials not configured)")
        return False

    # Check if within notification time window
    if notify_start or notify_end:
        now = datetime.now(FINNISH_TZ)
        if notify_start and now < notify_start:
            print(f"  Skipping Pushover notification (before window: {notify_start})")
            return False
        if notify_end and now > notify_end:
            print(f"  Skipping Pushover notification (after window: {notify_end})")
            return False

    # Only notify on yellow or better
    if traffic_light not in ("yellow", "red"):
        print("  Skipping Pushover notification (indicator below yellow)")
        return False

    # Format the notification
    prob_str = f"{aurora_prob:.0f}%" if aurora_prob is not None else "N/A"
    clouds_str = f"{clouds:.0f}%" if clouds is not None else "N/A"

    title = f"Aurora in {location_name} • {indicator:.0f}% Chance"
    message = f"NOAA Probability: {prob_str}\nCloud Coverage: {clouds_str}"

    # Prepare the request
    data = urllib.parse.urlencode({
        "token": pushover_token,
        "user": pushover_user,
        "title": title,
        "message": message
    }).encode("utf-8")

    try:
        request = urllib.request.Request(
            "https://api.pushover.net/1/messages.json",
            data=data,
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status == 200:
                print("  Pushover notification sent successfully")
                return True
            else:
                print(f"  Pushover notification failed: HTTP {response.status}")
                return False
    except urllib.error.URLError as e:
        print(f"  Pushover notification failed: {e}")
        return False


def parse_datetime(s: str) -> datetime:
    """Parse datetime string in format 'YYYY-MM-DD HH:MM' as Finnish time."""
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=FINNISH_TZ)


def main():
    """Main function to fetch all data and write to JSON."""
    parser = argparse.ArgumentParser(description="Fetch aurora observation data")
    parser.add_argument("--location", default="Oulu", help="Location name for notifications")
    parser.add_argument("--lat", type=float, default=65.01, help="Latitude")
    parser.add_argument("--lon", type=float, default=25.47, help="Longitude")
    parser.add_argument("--output", default="current_observation_oulu.json", help="Output JSON file")
    parser.add_argument("--badges", action="store_true", help="Generate badge files")
    parser.add_argument("--notify-start", type=parse_datetime, help="Notification window start (Finnish time, format: 'YYYY-MM-DD HH:MM')")
    parser.add_argument("--notify-end", type=parse_datetime, help="Notification window end (Finnish time, format: 'YYYY-MM-DD HH:MM')")
    args = parser.parse_args()

    print(f"Fetching aurora observation data for {args.location} ({args.lat}, {args.lon})...")

    # Fetch all data
    clouds = fetch_cloud_coverage(args.lat, args.lon)
    print(f"  Cloud coverage: {clouds}%")

    aurora_point, aurora_region = fetch_ovation_data(args.lat, args.lon)
    print(f"  Aurora probability (point): {aurora_point}%")
    print(f"  Aurora probability (region): {aurora_region}%")

    kp_observed, kp_3h, kp_6h = fetch_kp_indices()
    print(f"  KP index (observed): {kp_observed}")
    print(f"  KP index (3h): {kp_3h}")
    print(f"  KP index (6h): {kp_6h}")

    bz, bt = fetch_solar_wind()
    print(f"  Bz: {bz} nT")
    print(f"  Bt: {bt} nT")

    # Calculate derived values
    indicator = calculate_aurora_indicator(aurora_point, clouds)
    traffic_light = calculate_traffic_light(indicator)

    print(f"  Aurora indicator: {indicator}%")
    print(f"  Traffic light: {traffic_light}")

    # Build output JSON
    output = {
        "last-update": int(time.time()),
        "cloud-coverage": clouds,
        "aurora-probability": aurora_point,
        "aurora-probability-region": aurora_region,
        "kp-index": kp_observed,
        "kp-index-3h": kp_3h,
        "kp-index-6h": kp_6h,
        "bz": bz,
        "bt": bt,
        "aurora-indicator": indicator,
        "aurora-traffic-light": traffic_light
    }

    # Write to file
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nData written to {args.output}")

    # Generate badge files for shields.io (only if requested)
    if args.badges:
        write_badges(traffic_light, aurora_point, clouds, kp_observed, bz, bt)
        print("Badges written to badges/")

    # Send push notification
    send_pushover_notification(args.location, indicator, aurora_point, clouds, traffic_light,
                               args.notify_start, args.notify_end)


if __name__ == "__main__":
    main()
