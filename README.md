# Oulu Aurora Tracker

[![Current Status](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/badges/recommendation.json)](current_observation_oulu.json)
[![Aurora Probability](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/badges/aurora-probability.json)](current_observation_oulu.json)
[![Cloud Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/badges/cloud-coverage.json)](current_observation_oulu.json)
[![KP Index](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/badges/kp-index.json)](current_observation_oulu.json)
[![Bz](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/badges/bz.json)](current_observation_oulu.json)
[![Bt](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/badges/bt.json)](current_observation_oulu.json)

A real-time aurora borealis visibility tracker for Oulu, Finland. This repository automatically fetches space weather data every 15 minutes and compiles it into a simple JSON file that can be used by applications, websites, or personal dashboards.

**Note:** This project will only be active until Mid-February 2026.

## Quick Start

The latest aurora data is available in [`current_observation_oulu.json`](current_observation_oulu.json), updated every 15 minutes via GitHub Actions.

**Badge colors at a glance:**
- **Red** = Perfect
- **Yellow** = Good
- **Green** = Okay
- **Gray** = Not favorable

## Understanding the Data

The JSON file contains multiple data points that together help predict whether you'll see the aurora borealis. Here's what each value means in plain language:

### `last-update`
**Unix timestamp of when the data was last fetched.**

This is the number of seconds since January 1, 1970. You can convert this to a human-readable date in most programming languages or at [unixtimestamp.com](https://www.unixtimestamp.com/).

---

### `comment`
**Status message about data availability, or `null` if all data was fetched successfully.**

When one or more data sources are temporarily unavailable (API outages, network issues, etc.), the system falls back to the last known values for those fields. This field tells you which values are stale:

| Value | Meaning |
|-------|---------|
| `null` | All data is fresh from the APIs |
| `"No reports found for Bz and Bt. Using last known data!"` | Example: Bz and Bt are using cached values |

---

### `cloud-coverage`
**Percentage of sky covered by clouds (0-100%).**

Clouds are the aurora hunter's worst enemy. You can have perfect space weather conditions, but if clouds block your view of the sky, you won't see anything. This value comes from Norway's meteorological service forecast for Oulu.

| Value | Meaning |
|-------|---------|
| 0-25% | Clear skies - excellent viewing conditions |
| 25-50% | Partly cloudy - you might see aurora through gaps |
| 50-75% | Mostly cloudy - limited visibility, but still possible |
| 75-100% | Overcast - very unlikely to see anything |

---

### `aurora-probability`
**NOAA's predicted aurora probability at Oulu's exact location (65°N, 25°E).**

This value comes from NOAA's OVATION model, which uses real-time solar wind measurements to predict where aurora will appear around the globe. The percentage represents the likelihood of aurora activity occurring at this specific point - assuming clear skies. **This is purely a space weather prediction and does not account for cloud coverage.**

---

### `aurora-probability-region`
**Average aurora probability for the region around Oulu (64-66°N, 24-26°E).**

Aurora displays can span large areas of the sky, so looking at a single point doesn't tell the whole story. This regional average covers a 2° × 2° area centered roughly on Oulu, giving you a better sense of overall aurora activity in your viewing area.

---

### `kp-index`
**The planetary K-index (0-9) - a global measure of geomagnetic disturbance.**

The Kp index measures how disturbed Earth's magnetic field is on a scale from 0 (very quiet) to 9 (extreme storm). When solar wind interacts with our magnetosphere, it creates disturbances that scientists detect using magnetometers around the world. Higher Kp values mean the aurora oval expands further from the poles and the lights become more intense.

| Kp | What to expect in Oulu (65°N) |
|----|------------------------------|
| 0-2 | Aurora possible but faint, look to the north |
| 3-4 | Good aurora likely, may appear overhead |
| 5-6 | Strong display, visible across much of the sky |
| 7-9 | Intense geomagnetic storm - spectacular but rare |

**For Oulu's latitude, Kp 3+ typically means a worthwhile show.**

---

### `kp-index-3h` and `kp-index-6h`
**Predicted Kp index for 3 and 6 hours from now.**

These forecasts help you plan ahead. If the current Kp is low but rising in the forecast, you might want to wait before bundling up and heading outside.

---

### `bz`
**The north-south component of the interplanetary magnetic field (in nanotesla, nT).**

This is perhaps the most important real-time indicator for aurora hunters. The sun constantly blows a "wind" of charged particles toward Earth, and this solar wind carries its own magnetic field. The Bz value tells you which direction that magnetic field is pointing:

- **Negative Bz (southward):** This is what you want. When the solar wind's magnetic field points south, it can connect with Earth's northward-pointing field, allowing energy and particles to pour into our atmosphere. Think of it as "opening the door" for aurora.
- **Positive Bz (northward):** The magnetic fields repel each other, and Earth's magnetosphere stays closed. Aurora activity is suppressed.

| Bz Value | What it means |
|----------|---------------|
| > +5 nT | Door firmly closed - aurora suppressed |
| 0 to +5 nT | Neutral - other factors will determine activity |
| 0 to -5 nT | Door opening - conditions becoming favorable |
| -5 to -10 nT | Door wide open - expect enhanced aurora |
| < -10 nT | Excellent conditions - strong aurora likely |

---

### `bt`
**The total strength of the interplanetary magnetic field (in nanotesla, nT).**

While Bz tells you the direction, Bt tells you the overall strength of the magnetic field carried by the solar wind. Higher Bt values mean more magnetic energy is available to interact with Earth's field. The combination of high Bt and strongly negative Bz creates the best conditions for aurora.

| Bt Value | Strength |
|----------|----------|
| < 5 nT | Weak |
| 5-10 nT | Moderate |
| 10-20 nT | Strong |
| > 20 nT | Very strong (often during solar storms) |

---

### `aurora-indicator`
**A practical score (0-100) combining aurora probability with local visibility.**

This is a simple calculation: take the NOAA OVATION aurora probability and adjust it for cloud coverage.

**Formula:**
- 0-50% clouds: No penalty - full aurora probability
- 50-100% clouds: Linear penalty down to 0% at complete overcast

For example:
- 40% aurora probability + 30% clouds = **40%** indicator
- 40% aurora probability + 75% clouds = **20%** indicator (half visibility)
- 40% aurora probability + 100% clouds = **0%** indicator (can't see sky)

| Score | Meaning |
|-------|---------|
| 0-10% | Very low chance - probably not worth going outside |
| 10-25% | Low chance - only for the dedicated |
| 25-50% | Moderate chance - worth checking the sky |
| 50%+ | Good chance - get outside! |

---

### `aurora-traffic-light`
**A simple color indicator for quick decision-making.**

| Color | Meaning | Indicator Score |
|-------|---------|-----------------|
| `red` | Go outside now! Excellent chance of seeing aurora | 50%+ |
| `yellow` | Worth checking - moderate chance of aurora | 25-50% |
| `green` | Possible but unlikely - for enthusiasts only | 10-25% |
| `black` | Don't bother - very low chance or sky not visible | < 10% |

---

## Learn More

Want to dive deeper into aurora forecasting? This video provides an excellent explanation of all the key concepts:

**[Understanding Aurora Forecasts - YouTube](https://www.youtube.com/watch?v=PLrrwrTJ2KQ)**

---

## Data Sources

This project aggregates data from the following public APIs:

| Data | Source | API Endpoint |
|------|--------|--------------|
| Cloud Coverage | [MET Norway](https://api.met.no/) | [Location Forecast](https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=65.01&lon=25.47) |
| Aurora Probability | [NOAA SWPC](https://www.swpc.noaa.gov/) | [OVATION Aurora](https://services.swpc.noaa.gov/json/ovation_aurora_latest.json) |
| Kp Index | [NOAA SWPC](https://www.swpc.noaa.gov/) | [Kp Forecast](https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json) |
| Bz/Bt Values | [NOAA SWPC](https://www.swpc.noaa.gov/) | [Solar Wind Mag Field](https://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json) |

**Note:** NOAA's OVATION model predicts aurora based purely on space weather conditions. It does not account for cloud coverage or other terrestrial visibility factors - that's why this project combines it with weather data.

---

## Example Output

```json
{
  "last-update": 1706745600,
  "comment": null,
  "cloud-coverage": 15.0,
  "aurora-probability": 45.0,
  "aurora-probability-region": 42.5,
  "kp-index": 4.0,
  "kp-index-3h": 4.33,
  "kp-index-6h": 3.67,
  "bz": -8.2,
  "bt": 12.4,
  "aurora-indicator": 45.0,
  "aurora-traffic-light": "yellow"
}
```

---

## Using the Data

The JSON file is publicly accessible. You can fetch it directly:

```bash
curl https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/current_observation_oulu.json
```

Or use it in your Swift applications:

```swift
struct AuroraObservation: Codable {
    let lastUpdate: Int
    let comment: String?
    let cloudCoverage: Double?
    let auroraProbability: Double?
    let auroraProbabilityRegion: Double?
    let kpIndex: Double?
    let kpIndex3h: Double?
    let kpIndex6h: Double?
    let bz: Double?
    let bt: Double?
    let auroraIndicator: Double
    let auroraTrafficLight: String

    enum CodingKeys: String, CodingKey {
        case lastUpdate = "last-update"
        case comment
        case cloudCoverage = "cloud-coverage"
        case auroraProbability = "aurora-probability"
        case auroraProbabilityRegion = "aurora-probability-region"
        case kpIndex = "kp-index"
        case kpIndex3h = "kp-index-3h"
        case kpIndex6h = "kp-index-6h"
        case bz, bt
        case auroraIndicator = "aurora-indicator"
        case auroraTrafficLight = "aurora-traffic-light"
    }
}

let url = URL(string: "https://raw.githubusercontent.com/bennokress/Oulu-Aurora/main/current_observation_oulu.json")!
let (data, _) = try await URLSession.shared.data(from: url)
let observation = try JSONDecoder().decode(AuroraObservation.self, from: data)

if observation.auroraTrafficLight == "red" {
    print("Aurora alert! Go outside now!")
}
```

---

## License

This project is licensed under the [European Union Public Licence v1.2](LICENSE.md).

Data from MET Norway is used under their [free data license](https://api.met.no/doc/License).
NOAA data is public domain.
