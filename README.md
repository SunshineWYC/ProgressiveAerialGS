# ProAGS project page

Project website for **Progressive Gaussian Splatting for High-Fidelity 3D Reconstruction of Large Scale Remote Sensing Scenes**.

- Website: https://sunshinewyc.github.io/ProgressiveAerialGS/
- Paper authors: Yongchang Wu, Zhenwei Shi, and Zhengxia Zou.
- Journal: IEEE Geoscience and Remote Sensing Magazine, 2026.

## Branches

`main` is reserved for the research code. `project_page` contains this website and has an independent commit history. Do not merge the website branch into `main`.

## Local preview and checks

The site uses static HTML, CSS, and JavaScript without a build step.

```sh
python scripts/preview.py --port 8127
python scripts/check_site.py --release
```

Open http://127.0.0.1:8127/ for the local preview. Edit `site/index.html` and `site/assets/` for website updates.

## Deployment

GitHub Pages uses GitHub Actions. A push to `project_page` runs the release check and deploys **only `site/`**. The `github-pages` environment is restricted to this branch. Changes on `main` do not update the website.

Original manuscripts, source charts, private working notes, and local preview files are excluded from Git and deployment. See `NOTICE.md` for template attribution; research materials retain their respective rights.
