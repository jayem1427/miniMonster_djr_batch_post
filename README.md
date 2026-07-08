# Batch Post

An Autodesk Fusion add-in that **batch post-processes** CAM operations into one or more G-code files.

It is especially useful on **Fusion Personal**, which cannot normally post multi-tool NC programs in one pass: the add-in posts operations individually through your chosen post-processor, then merges the results.

Works with **any** Fusion post-processor (LinuxCNC, Mach, Fanuc, custom `.cps`, etc.).

## Features
- Output one file per operation, per setup, per setup and tool, or a single combined file
- Multi-tool programs on Fusion Personal (post per operation, then merge)
- Optional A-axis rotation between setups for indexed milling
- Optional restoration of rapid moves (`G1` → `G0` on non-cutting retracts)
- Combine consecutive operations that use the same tool
- Configurable header/tail detection, line numbering, and output naming

## Acknowledgments

This project is a generalized fork of the [Makera Community Fusion Plugin](https://github.com/Carvera-Community/CarveraCommunity_FusionPlugin), originally created for the Makera / Carvera community. That work was itself heavily inspired by Tim Paterson’s [PostProcessAll](https://github.com/TimPaterson/Fusion360-Batch-Post).

Credit to those authors and communities for the original design and ideas. This fork rebrands the tool as a **machine-agnostic** batch post utility and drops vendor-specific product branding from the UI and docs.

## Requirements
- Autodesk Fusion (Personal Edition or paid)
- A Fusion post-processor for your CNC (`.cps`)

## Installation
This plugin follows the normal local add-in install procedure for Fusion.

1. Clone the repository into a folder of your choice:

```bash
# SSH:
git clone git@github.com:jayem1427/miniMonster_djr_batch_post.git "Batch Post"

# OR HTTPS:
git clone https://github.com/jayem1427/miniMonster_djr_batch_post.git "Batch Post"
```

2. In Fusion: **Utilities → Scripts and Add-Ins…**
3. Click **+** → **Script or add-in from device**
4. Select the folder that contains `Batch Post.manifest`
5. (Optional) Enable **Run on startup**
6. You should see a new icon in the **Manufacture** workspace (near Setup sheet / Milling)

## Usage
This utility is **not** a post-processor. You still need an **NC Program** in Fusion that points at your post-processor (and optionally a machine configuration).

1. Create an NC Program with the normal Fusion post dialog and select your `.cps` file.
2. You must select a **post processor** on the NC Program.
3. A **machine configuration** is optional. Without one, posting uses your post-processor settings only. Attach a machine if you need **A-axis rotation between setups** or **ATC slot assignment** in the Tools tab.
4. Open **Batch Post**, select the NC Program and setups, configure output options, and click **Process**.

### Tabs
There are four tabs ordered as a workflow: [Input Selection](#input-selection-tab), [G-code Options](#g-code-options), [Output Options](#output-options) and [Misc](#misc). Settings on each tab are saved to the document as they change. The only settings that are not saved are `Overwrite existing files` and `Clear output folder`.

You can also save default settings locally for new documents.

#### Input Selection Tab

Select the **NC Program** that holds your post-processor settings. The dialog shows the optional **Machine** and required **Post Processor**.

Select setups in the table (order matters for A-axis rotation). Setups with incompatible WCS may be greyed out unless A-axis rotation is enabled and a machine with an A-axis is attached.

Use **Process** to run the add-in, or **Close** to exit without posting.

#### G-code Options

- **Rotate A-Axis between setups** — inject A-axis moves between setups (requires a machine with an A-axis)
- **Retract Y on A-axis rotation** / **Y-retraction coordinate** — optional Y retract in G53 before rotating
- **Restore rapid moves** — experimental: convert qualifying retract/traverse/plunge patterns from `G1` to `G0` (validate with a viewer such as [NCViewer](https://ncviewer.com))
- **Add line numbers** — optional N-word numbering
- **G-code blocks** — tool-change preamble, end-of-program markers (`M5`/`M9`/`M30` by default), and header-end markers (`G20`/`G21` by default)

#### Output Options

- **Output folder** and **File name** (extension comes from the post-processor)
- **Operations grouping**: Single file / Group on Setup / Group on Setup and Tool / One file per Operation
- **Combine operations using same tool**
- Flat file structure, sequence numbers, numeric-only names, overwrite, and clear-folder options

#### Misc

Language selection and setup rename (search/replace, optional regex).

## Development

```bash
git checkout -b dev
git commit -m "Describe your changes"
git push -u origin dev
```

## Project Structure (key files)
- `Batch Post.py` – main add-in entry point
- `config.py` – global configuration
- `commands/` – Fusion command modules
- `commands/postProcessor` – batch post-processing logic
- `commands/postProcessor/dialog` – UI
- `commands/postProcessor/resources/i18n` – translations
- `lib/` – shared helpers

## Contributing
- Fork the repository and open pull requests against `dev`.
- Follow the project's code style and write clear commit messages.

## License
GNU General Public License v2.0

## Contact
Use GitHub issues for any issues
