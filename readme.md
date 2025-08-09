# Fujifilm EXIF Renamer (with Recipes)

A tiny Python + exiftool helper to **inspect EXIF** and **rename photos** based on camera settings.  
Optionally matches your shots against **custom “recipes”** (Vibrant Arizona, Reggie's Portra and some other of the recipes that I am using) and uses the recipe name in the filename e.g. `DSCF2289_[HDR][01][VibrantArizona].JPG`

---

## Installation

You will need [Alfred with powerpack](https://www.alfredapp.com/powerpack/) and [exiftool](https://formulae.brew.sh/formula/exiftool) installed.

Download alfred workflow from this repo and add it to Alfred.

## Name Tags

This utility will add the following tags to the filename:

- `HDR` from **PictureMode**
- **SequenceNumber** (always, if > 0): `[01]`
- **DriveMode**: `[CL01]`, `[CH01]`, or `[EB01]` if present 
- **Film simulation** from **FilmMode** or a matching **Recipe** name, if recipe settings are found.

## Custom Recipes

Fuji doesn't provide information about custom recipe name or index, but we can deduce it from the settings.

By default, detection of the next recipes is included:
- Reggies Portra
- Alpine Negative
- Cinestill 500T
- Classic Cuban Neg
- Leica X
- Vibrant Arizona

You can add your own recipes in alfred workflow settings, here are example of custom recipe:

```json
[
    {
        "name": "Reggies Portra",
        "settings": {
            "FilmMode": "Classic Chrome",
            "DynamicRangeSetting": "Auto",
            "HighlightTone": "-1 (medium soft)",
            "ShadowTone": "-1 (medium soft)",
            "Saturation": "+2 (high)",
            "NoiseReduction": "-4 (weakest)",
            "Sharpness": "Soft",
            "Clarity": 0,
            "GrainEffectRoughness": "Weak",
            "GrainEffectSize": "Small",
            "ColorChromeEffect": "Strong",
            "ColorChromeFXBlue": "Weak",
            "WhiteBalance": "Auto",
            "WhiteBalanceFineTune": "Red +40, Blue -80"
        }
    },
    {
        "name": "Vibrant Arizona",
        "settings": {
            "FilmMode": "Classic Chrome",
            "DRangePriority": "Fixed",
            "DRangePriorityAuto": "Strong",
            "HighlightTone": "0 (normal)",
            "ShadowTone": "0 (normal)",
            "Saturation": "+4 (highest)",
            "NoiseReduction": "-4 (weakest)",
            "Sharpness": "Soft",
            "Clarity": -3,
            "ColorChromeEffect": "Off",
            "ColorChromeFXBlue": "Weak",
            "GrainEffectRoughness": "Weak",
            "GrainEffectSize": "Small",
            "WhiteBalance": "Manual",
            "ColorTemperature": 4350,
            "WhiteBalanceFineTune": "Red +120, Blue -160"
        }
    }
]
```

## Troubleshooting

### JSON is not valid

Make sure you have correct JSON before pasting it into the workflow settings. 

### Recipe is not applied

You can check the correct values for recipe mathcing by enabling **Write log** in the workflow settings and checking the log output in workflow directory or by uploading a photo to some online EXIF viewer e.g. [jimpl](https://jimpl.com) 

If this tool is not applying recipe name after you added it, check the log file, it will print out all the settings that it is trying to match against your recipe.
