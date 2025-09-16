# 🏠 Understanding This Dotbot Repository

This repository uses [Dotbot](https://github.com/anishathalye/dotbot) to manage dotfiles. Dotbot is a lightweight tool that creates symlinks from the home directory to files in the dotfiles repository based on a YAML configuration. Unlike more complex dotfile managers like Chezmoi, which uses templating, encryption, and state management, Dotbot takes a minimalist approach, making it easy to understand and debug.

## 🚀 Installation

Clone this repository into `~/.dotfiles` and run the install script:

```bash
git clone <repository-url> ~/.dotfiles
cd ~/.dotfiles
./install mac  # For macOS
```

This works even on a freshly installed system.

## ⚙️ How It Works

The core of this system is the `./install` script, which is a wrapper around Dotbot. When you run it, Dotbot reads YAML configuration files and performs the specified actions:

```bash
./install mac
```

This command runs on two config files:
1. First, it processes `install.conf.yaml` (the base configuration)
2. Then it processes `mac.conf.yaml` (the environment-specific configuration)

## 🌍 Multi-Environment Support

The repository supports multiple environments through separate configuration files:

- [`install.conf.yaml`](install.conf.yaml) - Base configuration applied to all environments
- [`mac.conf.yaml`](mac.conf.yaml) - My macOS-specific configurations
- Additional `*.conf.yaml` files can be created for other environments

`mac.conf.yaml` is my only public environment-specific config, so you'll have to use your imagination and pretend there are several. At work, I maintain a private branch with work-specific configuration. Running `./install work` applies both the base configuration and `work.conf.yaml`.

The install script applies configurations in order, allowing environment-specific settings to override or extend the base configuration.

## 🔧 Local Override Pattern

A key design in _my_ dotfiles is the use of `.local` files for environment-specific overrides. The base configuration files source their `.local` counterparts if they exist:

- `.zshrc` → sources `.zshrc.local`
- `.alias` → sources `.alias.local`
- `.env` → sources `.env.local`
- `.gitconfig` → includes `.gitconfig.local`

The environment-specific configurations (like [`mac.conf.yaml`](mac.conf.yaml)) create these `.local` symlinks pointing to actual environment files:

```yaml
~/.alias.local:
  path: alias.mac
~/.env.local:
  path: env.mac
~/.zshrc.local:
  path: zshrc.mac
```

This pattern allows the base configuration to remain generic while supporting environment-specific customizations, _without_ introducing the complexity environment-specific git branches or using templates.

## 🚀 Dotbot features

My configuration files use standard Dotbot features:

1. 📦 Update git submodules (Oh My Zsh plugins, Powerlevel10k theme, vim plugins)
2. 📂 Create directories (`~/.bin`)
3. 🔗 Create symlinks from the home directory to files in this repository
4. 🧹 Cleans up broken symlinks

In addition, you can run arbitrary shell commands during the installation process. I use this in [`mac.conf.yaml`](mac.conf.yaml) to inject secrets into scripts with 1Password.

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

##  Conclusion

The beauty of Dotbot is its simplicity and that configuration files are version controlled without the downsides of having a git repository at the root of `$HOME`.