source ~/.alias

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/Craig/tools/google-cloud-sdk/path.fish.inc' ]; . '/Users/Craig/tools/google-cloud-sdk/path.fish.inc'; end
set PATH $HOME/.jenv/bin $PATH
status --is-interactive; and source (jenv init -|psub)

set PATH /usr/local/opt/python@3.8/bin $PATH

# Created by `userpath` on 2020-04-30 16:39:16
set PATH $PATH /Users/Craig/.local/bin
