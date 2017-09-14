" Modified by Arjun Krishnan, 2013. 

" Mar 17 2017 Requires SearchInRuntime. Should run :scriptnames, store output
" of the command into a variable, and search for 'searchInRuntime.vim' This
" involves using redir to capture the scriptnames command

" Aug 31 2014 I'm writing a function that takes a markdown file and adds a table of contents
" Right now, it assumes the content is all markdown, and works with mypersonalblog1984
" added two new functions write_markdown_toc and del_markdown_toc
" DelMarkdownToc appears to work as of Aug 31 2014

" Jan 19 2015 Added new feature: will use gnome login keyring if possible. Otherwise, set the variables blog_username, blog_password and blog_url in the settings section manually.
" gnomekeyring works well. should document requirements.

" Issues and To do
" - Wordpress does not like internal references. Although doctoc inserts these
" into markdown, unless the markdown is converted to html using standard markdown or pandoc, the links do not work. So typically avoid table of contents.
" - Make the BlogSend command save a temporary copy of the file before sending. In fact, make a simple function that saves the file. It should take in a startline for the buffer and save until EOF.
" I keep getting the init() errors. the blog_login_success variable does not seem to be persistent.
" Fixed the init error, but the problem is raw_input inside of vim. I want to
" run a shell command that can accept input from outside vim, but this seems
" quite messy. Seems like one way to do it is to call an external script.

" Copyright (C) 2007 Adrien Friggeri.
"
" This program is free software; you can redistribute it and/or modify
" it under the terms of the GNU General Public License as published by
" the Free Software Foundation; either version 2, or (at your option)
" any later version.
"
" This program is distributed in the hope that it will be useful,
" but WITHOUT ANY WARRANTY; without even the implied warranty of
" MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
" GNU General Public License for more details.
"
" You should have received a copy of the GNU General Public License
" along with this program; if not, write to the Free Software Foundation,
" Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.  
" 
" Maintainer:	Adrien Friggeri <adrien@friggeri.net>
" URL:		http://www.friggeri.net/projets/vimblog/
" Version:	0.9
" Last Change:  2007 July 13
"
" Commands :
" ":BlogList"
"   Lists all articles in the blog
" ":BlogNew"
"   Opens page to write new article
" ":BlogOpen <id>"
"   Opens the article <id> for edition
" ":BlogSend"
"   Saves the article to the blog
"
" Configuration : 
"   Edit the "Settings" section (starts at line 51).
"
"   If you wish to use UTW tags, you should install the following plugin : 
"   http://blog.circlesixdesign.com/download/utw-rpc-autotag/
"   and set "enable_tags" to 1 on line 50
"
" Usage : 
"   Just fill in the blanks, do not modify the highlighted parts and everything
"   should be ok.

" To do
" - Make tags global variables and refer to them instead of having local definitions everywhere.

command! -nargs=0 BlogList exec("py blog_list_posts()")
command! -nargs=0 BlogNew exec("py blog_new_post()")
command! -nargs=0 BlogSend exec("py blog_send_post()")
command! -nargs=1 BlogOpen exec('py blog_open_post(<f-args>)')
command! -nargs=0 DelMarkdownToc exec('py del_markdown_toc()')
command! -nargs=0 WriteMarkdownToc exec('py write_markdown_toc()')

"python <<~/.vim/plugin/blog.py
if has('python')
    " must check if SearchInRuntime has been sourced already.
    let cmd = 'SearchInRuntime! pyfile blog.py2'
    "let cmd = 'pyfile ' . fnamemodify(getcwd(),'%:h') . '/blog.py2'
    "pyfile blog.py2
elseif has('python3')
    "py3file ~/.vim/plugin/vimpress/blog.py3
    let cmd = 'SearchInRuntime! py3file blog.py3'
endif
exec cmd
