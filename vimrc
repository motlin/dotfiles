" ⚠️ This comment will override any vim settings when editing this file.  These
" particular settings cause vim to use tabs not spaces
" vim: tabstop=4:shiftwidth=4:autoindent:smartindent:noexpandtab:softtabstop=0:cino=g0

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" ⚙️ General
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 🚀 Vim behavior, not vi
" This must be first, because it changes other options as side effect
set nocompatible

" 🔌 Use pathogen to easily modify the runtime path to include all plugins under
" " the ~/.vim/bundle directory
filetype off " force reloading *after* pathogen loaded
call pathogen#helptags()
execute pathogen#infect()

" 📋 Enable loading the plugin files and indent file for specific file types
filetype plugin indent on

" 📋 Number of lines of history to remember
set history=1000

" ↩️ Number of levels of undo history
set undolevels=1000

" 🚫 Ignore these file extensions when completing names by pressing Tab
set wildignore+=*.swp,*.bak,*.class

" 🔤 Disable these characters as word dividers
set iskeyword+=_

" 🔍 Make searches case-insensitive, unless they contain upper-case letters
set ignorecase
set smartcase

" 🎯 Virtual editing means that the cursor can be positioned where there is no
" actual character.  This can be halfway into a tab or beyond the end of the
" line.  Useful for selecting a rectangle in Visual mode and editing a table.
set virtualedit=all

" ⌫ Allow backspacing over autoindent, line breaks (join lines), start of insert
set backspace=indent,eol,start

" 💾 Write the contents of the file, if it has been modified, after certain
" commands
set autowrite

" 🌐 Affects the output of :TOhtml
:let html_use_css = 1
:let use_xhtml = 1

" 🗄️ store status information
set viminfo='1000,f1,<500,%

" 🙈 hide buffers instead of closing them
set hidden

" 🚫 Don't write backup files
set nobackup
set noswapfile

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 🎨 Theme/Colors
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
set background=dark

" 💡 Switch syntax highlighting on, when the terminal has colors
if &t_Co > 2 || has("gui_running")
	syntax on
endif

" 🌈 A 256 color scheme
if &t_Co >= 256 || has("gui_running")
	colorscheme inkpot
endif

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 👀 Visual cues
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 🔄 When a bracket is inserted, briefly jump to the matching one.
set showmatch

" 📌 When there is a previous search pattern, highlight all its matches.
set hlsearch

" 🔍 Use emacs-like incremental search (find as you type)
set incsearch

" 📦 Strings to use in 'list' mode.  Enable list mode with :set list
set listchars=tab:>-,trail:_,eol:$,nbsp:%,extends:#

" 🔇 No audio or visual bell
set novisualbell
set noerrorbells

" 📍 Show the line and column number of the cursor position
set ruler

" 🏷️ Change the terminal's title
set title

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 📝 Text formatting
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
set tabstop=4
set shiftwidth=4

set autoindent
set smartindent

" 📠 Tabs, not spaces!
" set noexpandtab

" 🤷 But just in case I'm working on a file with a more evil form of indentation
set expandtab

" 🏭 C-indenting option to make public and private labels not increase the
" indentation level
set cino=g0

autocmd Filetype gitcommit setlocal spell textwidth=72

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" ⌨️ Key mappings
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 👁️ Toggle display of unprintable characters
:map <F3> :set list!<CR>

" 🔍 Toggle search highlighting
:map <F5> :set hls!<bar>set hls?<CR>

" 📜 Ignore whitespace in diff views (vim -d file1 file2)
:map <F9> :set diffopt+=iwhite<CR>

" 📋 Toggle paste mode.  Everything is inserted literally - no indending
set pastetoggle=<F10>

" 🔢 Toggle line numbers
:map <F12> :set number!<CR>

" ↕️ Ctrl j/k to navigate horizontal splits
map <C-J> <C-W>j<C-W>_
map <C-K> <C-W>k<C-W>_
set wmh=0
" ↔️ Ctrl h/l to navigate vertical splits
map <C-H> <C-W>h<C-W><bar>
map <C-L> <C-W>l<C-W><bar>
set wmw=0

" 📝 Don't use Ex mode, use Q for formatting.  Wrap a block of text.
map Q gq

" 🔄 change the mapleader from \ to ,
let mapleader=","

" 💱 Use semi-colon instead of colon
nnoremap ; :

nnoremap <up> gk
nnoremap <down> gj

" ✖️ Clear highlighted searches
nmap <silent> ,/ :nohlsearch<CR>

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 🌟 Misc
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 🔄 Show the diffs between this buffer and the saved version of the file
function! s:DiffWithSaved()
  let filetype=&ft
  diffthis
  " new | r # | normal 1Gdd - for horizontal split
  vnew | r # | normal 1Gdd
  diffthis
  exe "setlocal bt=nofile bh=wipe nobl noswf ro ft=" . filetype
endfunction
com! Diff call s:DiffWithSaved()

" 📋 When editing a file, always jump to the last cursor position
autocmd BufReadPost *
\ if line("'\"") > 0 && line ("'\"") <= line("$") |
\   exe "normal! g'\"" |
\ endif

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 🔌 Stuff unique to my plug-ins/set-up
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" 🎯 Load matchit (% to bounce from do to end, etc.)
runtime! macros/matchit.vim

" 💳 Tab completion
function InsertTabWrapper()
	let col = col('.') - 1
	if !col || getline('.')[col - 1] !~ '\k'
		return "\<tab>"
	else
		return "\<c-p>"
	endif
endfunction

inoremap <tab> <c-r>=InsertTabWrapper()<cr>

" 🏷️ toggle the taglist window.
nnoremap <silent> <F8> :TlistToggle<CR>

" ➡️ cursor moves to the taglist window after opening the taglist window
let Tlist_GainFocus_On_ToggleOpen = 1

" 🚪 exit Vim if only the taglist window is currently opened
let Tlist_Exit_OnlyWindow = 1

" 🏷️ For use with ctags - most people won't need this
set tags=./tags,tags,../tags,../../tags,../../../tags,../../../../tags

" 🔀 Start diff mode with vertical splits (unless explicitly specified otherwise).
set diffopt+=vertical

" 🟡 Highlight whitespace at the end of the line in ugly yellow
match Todo /\s\+$/

" 🔠 Don't ignore case in search patterns.
set noignorecase

" 📊 tell VIM to always put a status line in, even if there is only one window
set laststatus=2

if has("multi_byte")
  if &termencoding == ""
    let &termencoding = &encoding
  endif
  set encoding=utf-8
  setglobal fileencoding=utf-8
  "setglobal bomb
  set fileencodings=ucs-bom,utf-8,latin1
endif

au BufRead,BufNewFile *.g4 set filetype=antlr4


" https://stackoverflow.com/a/37884871
set timeoutlen=1000
set ttimeoutlen=0
