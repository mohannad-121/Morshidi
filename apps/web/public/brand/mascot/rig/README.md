# Morshidi layered voice rig

All visual layers share the official mascot's `975 x 800` coordinate system. The React component applies these masks to `/brand/mascot/morshidi-mascot.png`; the original raster artwork remains unchanged.

- `body-base-mask.svg` keeps the head and torso stationary and retains shoulder overlap beneath the moving arms.
- `shoulder-restoration.png` is the preservation edit generated from the official mascot; `shoulder-restoration-mask.svg` exposes only the small hidden fabric regions beneath the original arm pixels.
- `arm-left-mask.svg` and `arm-right-mask.svg` isolate the original arm pixels for shoulder-pivot transforms.
- `mouth-closed.svg`, `mouth-half.svg`, and `mouth-open.svg` contain mouth-only artwork. They never cover the surrounding face, beard, glasses, or hair.

The React component selects mouth state only from remote assistant audio energy. Student microphone energy cannot animate the mouth. Gesture timing is implemented in CSS with long resting portions, and reduced-motion disables every arm transform.
