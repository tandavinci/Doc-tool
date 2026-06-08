# Application Icons

Place your application icon files here:

- `app-icon.ico` — Windows icon (required for taskbar, title bar, exe)
- `app-icon.png` — 512x512 PNG (optional, used as fallback and for Linux builds)

## Requirements for .ico file

- Must contain multiple sizes: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256
- Use a tool like https://icoconvert.com or ImageMagick to generate from a PNG

## Usage

Once `app-icon.ico` is placed here, run:
```
npm run dist
```
The icon will automatically be used for the window, taskbar, and packaged executable.
