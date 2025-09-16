# 🏠 Understanding This Dotbot Repository

This repository uses [Dotbot](https://github.com/anishathalye/dotbot) to manage dotfiles. Dotbot creates symlinks from the home directory to files in the dotfiles repository based on YAML configuration. Dotbot competes with Chezmoi but is simpler, avoiding the need for templating.

## 🚀 Installation

Clone this repository into `~/.dotfiles` and run the install script:

```bash
git clone https://github.com/motlin/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./install mac  # For macOS
```

This works even on a freshly installed system.

## ⚙️ How It Works

The `./install` script runs Dotbot:

```bash
./install mac
```

This command runs on two config files:
1. `install.conf.yaml` (the base configuration)
2. `mac.conf.yaml` (the named environment-specific configuration)

## 🌍 Multi-Environment Support

The repository supports multiple environments through separate configuration files:

- [`install.conf.yaml`](install.conf.yaml) - Base configuration applied to all environments
- [`mac.conf.yaml`](mac.conf.yaml) - My macOS-specific configurations
- Additional `*.conf.yaml` files can be created for other environments

`mac.conf.yaml` is my only public environment-specific config, so you'll have to use your imagination and pretend there are several. At work, I maintain a private branch where `./install work` would apply both base and work-specific configurations.

Configurations apply in order, allowing environment-specific settings to override the base.

## 🔧 Local Override Pattern

A key design in _my_ dotfiles is the use of `.local` files for environment-specific overrides. The base configuration files source their `.local` counterparts if they exist:

- `.zshrc` → sources `.zshrc.local`
- `.alias` → sources `.alias.local`
- `.env` → sources `.env.local`
- `.config/git/config` → includes `.config/git/config.local`

The environment-specific configurations (like [`mac.conf.yaml`](mac.conf.yaml)) create these `.local` symlinks pointing to actual environment files:

```yaml
~/.alias.local:
  path: alias.mac
~/.env.local:
  path: env.mac
~/.zshrc.local:
  path: zshrc.mac
```

This supports environment-specific customizations introducing the complexity of git branches or templates.

## 🚀 Dotbot features

My configuration files use standard Dotbot features:

1. 📦 Update git submodules (Oh My Zsh plugins, Powerlevel10k theme, vim plugins)
2. 📂 Create directories (`~/.bin`)
3. 🔗 Create symlinks from the home directory to files in this repository
4. 🧹 Cleans up broken symlinks

You can also run shell commands during installation. I use this in [`mac.conf.yaml`](mac.conf.yaml) to inject 1Password secrets.

## 📁 Configuration Files Overview

### 🐚 Shell Configuration

**[`.zshrc`](zshrc)** - Main Zsh configuration that sets up Oh My Zsh with the Powerlevel10k theme, configures shell behavior (history sharing, case-sensitive completion, emacs keybindings), and loads various plugins including zsh-autosuggestions, fzf, and syntax highlighting. It also integrates direnv, zoxide (replacing cd), and sources local overrides.

**[`.p10k.zsh`](p10k.zsh)** - Powerlevel10k theme configuration that defines the prompt layout with segments for OS icon, directory, and Git status on the left, and command status/execution time on the right.

### 🛠️ Development Tools

**[`.config/git/config`](config/git/config)** (like `.gitconfig`) - See [my blog post](https://motlin.com/docs/git/configuration) which explains my customizations in depth. Includes aliases, advanced log formatting with graph visualization, aggressive optimizations, automatic stashing during merges/rebases, and integration with git-absorb for fixup commits.

**[`.vimrc`](vimrc)** - Vim configuration that sets up pathogen for plugin management, enables quality-of-life improvements (smart searching, visual cues for whitespace, tab completion), and defines custom key mappings. Configures the inkpot color scheme and includes functions for viewing diffs.

### 🌐 Environment and Aliases

**[`.alias`](alias)** - Defines shell aliases for common commands including navigation (`up`, `up2`), ls commands using eza with icons, Git shortcuts, and replacements like `bat` for `cat`. Also includes utility aliases for lazygit, just, and timestamp formatting.

**[`.env`](env)** - Minimal environment configuration that extends PATH with local directories, sets vim as the default editor, configures less as the pager with specific options, and points to a ripgrep configuration file.

### 📦 Other Configurations

- 🔍 **[`.ripgreprc`](ripgreprc)** - Ripgrep search tool configuration
- 📁 **[`config/`](config/)** - Directory containing configurations for various tools:
  - 🦇 [`bat/`](config/bat/) - Syntax highlighting pager
  - ⚡ [`just/`](config/just/) - Command runner
  - 🔧 [`mise/`](config/mise/) - Development environment manager
  - 🔐 [`1Password/`](config/1Password/) - SSH agent integration
