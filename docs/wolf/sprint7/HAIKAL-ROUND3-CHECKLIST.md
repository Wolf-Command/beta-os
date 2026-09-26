# Haikal round 3 — commissioning checklist

Beta only: `http://127.0.0.1:8788/content-2.0`. Do not open port 8787. Sign in as yourself. The creative director assignment is what the desk should be using. This checklist does not mark the library staff-ready. You do that only if the desk matches what you see on the NAS.

Measured catalog (`state/nas-estate/FINAL-TRUTH-20260927.json`, 2026-09-27T02:37:13+08:00): 63246 searchable rows, 60474 with a thumbnail, 124 preview failures, 4787 still unknown brand, 0 inaccessible. The One has no files in this catalog.

1. Open Content Engine. The brand list should offer Atrium, Uma Blu, Selo Group, Habitat, Tropik, The One, Blu Zone Rainforest Resto, and Goss Group.
2. Switch brand. Atrium, Uma Blu, Selo, Habitat, and Tropik should show historical files. Blu Zone Rainforest Resto should show the Blu Zone logo set (34 files). Goss Group should show the three Goss logos. The One should be empty. Empty means this catalog has no file for that brand.
3. Search for a filename you already know (an old shoot, not the test upload). You should get that file, not an empty library.
4. Open a photo. The preview should be the picture. Open a video. It should play. If a card says the preview is not ready, check `state/nas-estate/exceptions.json` before treating the whole library as broken.
5. Download one file from the preview. The file that saves should be that photo or video.
6. Select several cards and use Download (ZIP). The zip should contain those files.
7. Upload one small photo of yours through Smart Upload, for a brand you actually use. When it finishes, search the library for that filename. It should appear. A test image from the engineering run is already on the NAS under `_Imports/Wolf-Library` and is named with `WOLF-TEST-UPLOAD`. You can ignore it.
8. If a brand you expect is missing, name the NAS folder. Do not rename or delete anything on the NAS. Unknown folders were left unknown on purpose when the folder name was not one of the eight brands (Tampah Reserve, loose imports, staff documents).

Stop and say what failed, with the brand and the filename. Do not use production.
