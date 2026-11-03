# Contributing

Contributions are welcome through forks and pull requests. Please open an issue first for a large feature or a substantial layout change.

## Fork → branch → pull request

1. Fork [gaur-adi/ubuntu-rainmeter-themes](https://github.com/gaur-adi/ubuntu-rainmeter-themes).
2. Clone your fork and create a branch:

   ```bash
   git clone https://github.com/YOUR-USERNAME/ubuntu-rainmeter-themes.git
   cd ubuntu-rainmeter-themes
   git switch -c add-my-theme
   ```

3. Make your changes. New themes belong in `themes/your-theme/`, with a valid `theme.json`, a README, a complete layout preview, and artwork source/credits. Do not submit images or fonts you are not entitled to share.
4. Validate locally:

   ```bash
   ./install.sh --list
   /usr/bin/python3 -m unittest discover -s tests -v
   ```

   Test an installation from a GNOME desktop session and document your Ubuntu/GNOME versions, GPU, display count, and any limitations. Never run the installer with `sudo`.

5. Commit and push your branch to your fork:

   ```bash
   git add .
   git commit -m "Add my theme"
   git push -u origin add-my-theme
   ```

6. Open a pull request from your fork's branch into this repository's `main`. Include a preview, a description, testing details, and any third-party attribution.

## Review and merging

`main` is protected. Contributions go through a pull request, the `test` check, and maintainer review. The repository owner, **@gaur-adi**, is the code owner for all files. New commits after an approval require another review. Resolve review conversations before merging.

The maintainer can use a pull-request-only administrative bypass for their own changes or exceptional cases. This does not give contributors direct push or merge permission. Forking and opening a PR do not grant write access to the upstream repository.

Do not include credentials, private keys, location caches, local desktop configuration dumps, or downloaded third-party packages. CI uses read-only repository permissions; keep contributions compatible with fork-based pull requests and do not introduce `pull_request_target` workflows that execute untrusted contributor code.
