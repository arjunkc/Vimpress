# To do
# 1. Sep 24 2017 To continue testing BlogSend and BlogNew, but have to do other things now
# 1. Sep 24 2017 Debugging type errors in blog_list_posts
# 1. Sep 24 2017 It allows no mechanism to switch between blogs easily. It's best to start a new vim instance to switch blogs now. Instead there should a function called BlogChange which will change the blog by resetting blog_username etc and rerunning blog_init.
# 1. If no metadata found, exit gracefully. Currently there are weird errors it
# throws. Should say something like Metadata not found or Meta data error
# 1. Fix pandoc conversion when downloading html from internet
# 1. ~~Add a postformat. This will be your from to format. If it's already in
# markdown, no conversion is necessary.~~
# 1. Mar 16 2017 Fix password on mypersonalblog1984
# 1. ~~Mar 16 2017 working on function to send the post. It has to convert the
# markdown back to html to send~~
# 1. make a function to extract all the tags, and ignore categories. Or better 
#    yet, just ignore all tags and categories for now.
# 1. enabling tags seems very painful. You have to add these things called terms manually. see notes.
# ~~2. I could implement a passphrase less key for less secure things in the
# roots keyring. So the function blog_init, etc should take arguments that I
# can reuse when I call a script with my own script. It can extract metadata
# directly from the file, I suppose, just like this thing. All this seems so
# cumbersome.~~
# python blog_sendpage.py "filename" "

# -*- coding: utf-8 -*-
import sys

#python 3 specific imports
if sys.version[0] == '3':
    import urllib3, xmlrpc.client
    py3 = True
    pyinput = input
    xmlrpclib = xmlrpc.client
else:
    import urllib2, xmlrpclib
    py3 = False
    pyinput = raw_input

import urllib, xml.dom.minidom, string , re

# modules for me
import os, traceback, socket, datetime
import subprocess
#timeout socket lets me time out buggy xmlrpc calls.
import secretstorage as ss
# must migrate to the keyring or secretstorage package and support multiple keyring types.

#####################
#      Settings     #
#####################

enable_terms = False #in the wordpress api, terms stands for both categories and tags
enable_gnome_keyring = True
# if you do not enable keyring, set the variables below
blog_username = ''
blog_password = ''
blog_url = ''
localtempdir = '/tmp'

socket.setdefaulttimeout(10) #set global timeout in 10 secs. could replace with local timeout, but what the hell

# default keyring. must already exist.
KEYRING_NAME='vimpress'
# application name. keyring items will be set with this application name. This is how we figure out which keyring item corresponds to this plugin.
APP_NAME='vimpress'

# use for debugging output
# debug levels are 0,1,2. 2 is a lot of debug
dbg = 1

# enable toc support for markdown. needs doctoc.
enable_toc_support = 1

# set default post_type
#posttype = 'post' # or page
default_post_type = 'post'

# see if called from within vim. to be manually set before calling the script
# to be mostly used for testing. It really ought to be determined automatically.
if dbg >= 2:
    sys.stdout.write("sys.argv[0]:" + sys.argv[0] + "\n")

if sys.argv[0].find("python") != -1:
    # it returns -1 on failure
    from_vim = False
else:
    # the content of sys.argv[0] from within vim is strange and irrelevant
    from_vim = True
    import vim 

if dbg >= 2:
    sys.stdout.write("Value of from_vim variable: " + str(from_vim) + "\n")

#########################
#      Global Constants #
#########################
TOC_START_STRING = '<!-- START doctoc generated TOC please keep comment here to allow auto update -->'
# Modify according to DOCTOC tag. That is, take a md file, run doctoc on it, and see the start and end comments for the doctoc generated TOC. If doctoc is updated, its quite likely that these strings will be updated.
TOC_END_STRING ='<!-- END doctoc generated TOC please keep comment here to allow auto update -->'
# The meta data uses the % sign as an identifier in a weird way.
META_DATA_START = '%=========== Meta ============'
META_DATA_END = '%========== Content ========== -->'
VIMSYNTAX = 'markdown'
VIMFILETYPE = 'markdown'
DOCTOCSTRING = '*generated with [DocToc](http://doctoc.herokuapp.com/)*'

#########################
#      Global variables #
#########################
blog_login_success = False

#####################
# Do not edit below #
#####################
# this is the xmlrpc serverproxy object that's returned on authentication with the blog.
global handler

# the edit variable is to set listing mode to readonly. i think its not implemented correctly. there ought to be a vim option to set to readonly mode.

edit = 1

############################################################
# python function definitions. look at end for main loop. ##
############################################################

def blog_test():
    # function tests if the blog username, password and url combo works.
    global blog_username, blog_password, handler
    try:
        # this seems to be the fastest test of blog credentials.
        # getCategories has been replaced by getTaxonomies
        l = handler.getTerms(0, blog_username, blog_password,'category')
        # if list posts successful, return 1
        return True
    except:
        sys.stderr.write("An error has occured in blog_test\n")
        if dbg >= 1:
            traceback.print_exc(file=sys.stdout)
        return False

def blog_init():
    global blog_login_success, enable_gnome_keyring, dbg, keyring_bus, handler, blog_url
    if dbg >= 1:
        sys.stdout.write("Running blog_init.\n")


    if not blog_login_success:
        # set login details
        if enable_gnome_keyring:
            keyring_bus = ss.dbus_init()
            if dbg >= 1:
                sys.stdout.write("Running blog_set_keyring_info()\n")
            blog_set_keyring_info()
            # this also sets blog_login_success
        elif from_vim:
            # if keyring not enabled, enter details manually
            enter_blog_details_vim()
            blog_login_success = blog_test()
        else:
            enter_blog_details_python()
            blog_login_success = blog_test()
    
    # now blog_username, blog_password and blog_url should be set from the keyring or directly in the script.

    # check if blog_login_success
    if not blog_login_success:
        sys.stderr.write("\nblog login failed\n")
    else:
        sys.stdout.write("\nblog login success\n")

def blog_set_keyring_info():
    # supports calling from a python shell and from within vim
    # if calling from a shell, set from_vim to False
    # sees if keyring items already exist by searching for the attribute APP_NAME in KEYRING_NAME. 
    # picks the first keyring item found - who has multiple blogs. nevertheless, this is a bug.
    global blog_post_type,blog_username, blog_password, blog_url, handler, blog_login_success, from_vim, blog_post_format,keyring_bus

    try: #catchall for this function
        # find keys created by the app. I'll assume the appname is unique. It's currently vimpress
        atts = {'appname':APP_NAME}
        keylist = ss.search_items(keyring_bus,atts)
        try:
            # try to loop through found keys will throw exception otherwise
            found_keys = True
            acceptkey = False
            for key in keylist:
                # key is an object with methods like get_label, get_attributes. 
                key_atts = key.get_attributes()
                blog_username = key_atts['username']
                blog_password = key.get_secret()
                blog_url = key_atts['url']
                blog_post_type = key_atts['post_type']
                blog_post_format = key_atts['post_format']
        

                # if debug enabled, print username password and url.
                if dbg >= 1:
                    print(blog_username, blog_password, blog_url, blog_post_type, blog_post_format)

                # ask whether to accept the current username?
                
                if from_vim:
                    vimcmd = "input('Use username " + blog_username + " (default=y/n)? ')"
                    useracceptkey = vim.eval(vimcmd) or 'y'
                    if dbg >= 1:
                        sys.stdout.write("\nuser acceptance key value: " + useracceptkey + "\n") 
                else:
                    # if called from shell
                    useracceptkey = pyinput('Use username ' + blog_username + ' (default=y/n)? ') or 'y'
                    
                if useracceptkey == 'y':
                    # set handler using the newly gained credentials
                    try:
                        handler = xmlrpclib.ServerProxy(blog_url).wp
                    except:
                        sys.stdout.write("Error setting handler in blog_set_keyring_info()")
                    blog_login_success = blog_test()
                    if dbg >= 1:
                        sys.stdout.write("Blog login successful: "+ str(blog_login_success) + "\n") 
                    if blog_login_success:
                        break
        except StopIteration:
            # did not find keys
            found_keys=False 
            sys.stderr.write("No keys found\n")
                
        # if keys were not found, or a key was found and the login was not successful. you can either choose to create a new key, or if you want to reselect a different key, blog_init
        if (not found_keys) or (not blog_login_success): 
            sys.stdout.write("No acceptable key found.")
            # the loop accepts username, password and url and tries to list blog entries. If it works, it creates a new item. If not, it asks if you want to reenter password.
            if from_vim:
                reenter_login = vim.eval("input('Create new user? (Y/n)')") or 'y'
            else:
                reenter_login = input('Create new user? (Y/n)') or 'y'
            # if blog_login_success is true if the keyfound is succesful, will not run the loop.
            while (not blog_login_success) and reenter_login == "y":
                if from_vim:
                    enter_blog_details_vim()
                else:
                    enter_blog_details_python()
                if dbg >= 1:
                    print (blog_username, blog_password, blog_url )

                # (re)set handler
                try:
                    handler = xmlrpclib.ServerProxy(blog_url).wp
                except:
                    sys.stdout.write("Error setting handler in blog_set_keyring_info()")

                # test if the blog works.
                blog_login_success = blog_test()
                if not blog_login_success:
                    # you might choose to not reenter even if blog_test failed.
                    if from_vim:
                        reenter_login = vim.eval("input('blog login failed. reenter details (default=y/n)? ')") or 'y'
                    else:
                        reenter_login = pyinput('blog login failed. reenter details (default=y/n)? ') or 'y'
                else:
                    #if blog_login_success
                    sys.stdout.write("Blog test succesful. Creating new keyring item.")
                    atts = {'username':blog_username,
                            'url':blog_url,
                            'appname':APP_NAME,
                            'post_type': blog_post_type,
                            'post_format': blog_post_format,
                            'enable_terms': str(enable_terms)
                            }
                    create_keyring_item(atts)
            #end while
        # end if (not found_keys) or (not blog_login_success): 
    except:
        # for general try catchall in blog_set_keyring_info
        sys.stderr.write("Error in blog_set_keyring_info")
        if dbg >= 1:
            traceback.print_exc(file=sys.stdout)

def create_keyring_item(atts):
    global blog_password, blog_url, blog_post_type, blog_post_format, keyring_bus
    cols = ss.get_all_collections()
    found_keyring = False
    try:
        for ring in cols:
            if ring.get_label() == KEYRING_NAME:
                found_keyring = True
    except:
        sys.stderr.write("Did not find default keyring:" + KEYRING_NAME)
        if dbg >= 1:
            traceback.print_exc(file=sys.stdout)
    try:
        if not found_keyring:
            # create the collection, and let it be ring
            ring = ss.create_collection(keyring_bus,KEYRING_NAME)

        label = blog_username + '@' + blog_url
        ring.create_item(label,atts,blog_password,replace=True)
    except:
        sys.stderr.write("Error creating item or new collection/keyring")
        if dbg >= 1:
            traceback.print_exc(file=sys.stdout)

            
def enter_blog_details_vim():
    global blog_username,blog_password,blog_url,blog_post_type,enable_terms,default_post_type,blog_post_format

    blog_username = vim.eval("input('Enter username: ')")
    # mismatch quotes to get vim.eval to work correctly; like bash
    # To self: see how to create a password prompt in python. This will display plaintext.
    blog_password = vim.eval("input('Enter password: ')")
    # if the user hits enter, the default url is accepted. 
    # https is needed for wordpress.com
    default_url = 'https://' + blog_username + '.wordpress.com/xmlrpc.php'
    command = 'input("Enter url (' + default_url + '): ")'
    # ive tested the blog_url statement out. it picks default_url if you just hit enter.
    blog_url = vim.eval(command) or default_url
    enable_terms = bool(vim.eval("input('Enable terms like categories and tags (False/True)? ')")) or False
    # there is also a function called set_post_type that is unused
    blog_post_type = vim.eval('input("Enter post type (default=post/page): ")') or default_post_type
    blog_post_format = vim.eval('input("Enter post format (default=html/markdown): ")') or 'html'

def enter_blog_details_python():
    global blog_username,blog_password,blog_url,blog_post_type,enable_terms,default_post_type,blog_post_format
    # shell version of above commands
    blog_username = pyinput('Enter username: ')
    blog_password = pyinput('Enter password: ')
    default_url = 'https://' + blog_username + '.wordpress.com/xmlrpc.php'
    blog_url = pyinput("Enter url (" + default_url + "): ") or default_url
    enable_terms = bool(pyinput('Enable terms like categories and tags (default=True/False)? ')) or False
    blog_post_type = pyinput("Enter post type (default=post/page): ") or default_post_type
    blog_post_format = pyinput("Enter post format (default=html/markdown): ") or 'html'

def blog_edit_off():
    global edit
    if edit:
      edit = 0
    # turn off editing abilities
    for i in ["i","a","s","o","I","A","S","O"]:
      vim.command('map '+i+' <nop>')

def blog_edit_on():
    global edit
    if not edit:
        edit = 1
        # unmap these things? why? I don't know the purpose of this function.
        for i in ["i","a","s","o","I","A","S","O"]:
            vim.command('unmap '+i)

def blog_send_post():
    global localtempdir,handler,blog_login_success

    if not blog_login_success:
        blog_init()
        # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.

    try:
        def get_line(what):
            start = 0
            while not vim.current.buffer[start].startswith('%'+what):
                # while not found % + what, increment the counter
                # for example, it could be %StrID 
                start +=1
            return start
        def get_meta(what): 
            # get meta data from vim file by parsing initial lines that start with %StrID
            start = get_line(what)
            end = start + 1
            while not vim.current.buffer[end][0] == '%':
                # while end does not start with %, increment; i.e., as soon as it starts with a %, end it
                # this means the current line of metadata has, which means tags can be split over several lines 
                end +=1
            return " ".join(vim.current.buffer[start:end]).split(":")[1].strip()
            # join all lines corresponding to the metadata element, split them and get the second word. The second word contains the data of the metadata. The first word is the metadata identifier.

        strid = get_meta("StrID")
        post_title = get_meta("Title")
        # make a list of categories and tags
        if enable_terms:
            cats = [i.strip() for i in get_meta("Cats").split(",")]
            tags = get_meta("Tags")
            # here goes code which modifies the categories and tags

        text_start = 0
        while not vim.current.buffer[text_start] == META_DATA_END:
            text_start +=1
        #endwhile

        # increment if possible so that its not in the %==Content line anymore
        text_start = min(text_start + 1, len(vim.current.buffer))
        # get text of blog post.
        text = '\n'.join(vim.current.buffer[text_start:])
        # increment the counter until you get to the content identifier line. Load the text of the buffer into the text variable.
        post_content = convert_html_markdown(text,from_format='markdown',to_format=blog_post_format)
        post = {'post_content': '',
                'post_title': post_title,
                'post_content': post_content,
                'post_status': 'publish',
               }
        sys.stdout.write("About to send blog post \n")
        try:
            if strid != '':
                if dbg >= 1:
                    sys.stdout.write("Posting using strid: %s \n" % strid)
                handler.editPost(0, blog_username,blog_password, strid, post)
            else:
                # if there is no str id, create a new post
                sys.stdout.write("There is no strid, will use handler to create new post\n")
                strid = handler.newPost(0, blog_username, blog_password, post)
          
                # update strID string in the metadata of current buffer.
                vim.current.buffer[get_line("StrID")] = "%StrID : "+strid
            sys.stdout.write("Successfully sent post.\n")
        except:
            sys.stderr.write("Error sending post.\n")
            traceback.print_exc(file=sys.stdout)

        vim.command('set nomodified')
        #end try region
    except:
        sys.stderr.write("An error has occured in the python function blog_send_post\n")
        if dbg >= 1:
            traceback.print_exc(file=sys.stdout)

def blog_new_post():
    global blog_login_success

    if not from_vim:
        # I should really allow this.
        sys.stderr.write("Cannot call blog_new_post from outside of vim")

    if not blog_login_success:
        blog_init()
        # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.
    def blog_get_cats():
        # gets categories
        l = handler.getTerms('', blog_username, blog_password,'category')
        s = ""
        for i in l:
            s = s + i["description"]+", "
        if s != "": 
            return s[:-2]
        else:
            return s
  
    del vim.current.buffer[:]
    blog_edit_on()
    #vim.command("set syntax="+VIMSYNTAX)
    #vim.command("set filetype="+VIMFILETYPE)
    vim.command("set syntax=markdown")
    vim.command("set filetype=markdown")
    # The latter command loads latexsuite
  
    write_post_metadata()
    vim.current.window.cursor = (len(vim.current.buffer), 0)
    vim.command('set nomodified')
    #vim.command('set textwidth=0')

def write_post_metadata(strid='',title='',cats='',tags=''):
    vim.current.buffer[0] = '<!--'
    vim.current.buffer.append(META_DATA_START)
    vim.current.buffer.append("%StrID : " + strid)
    vim.current.buffer.append("%Title : " + title)
    if enable_terms:
        vim.current.buffer.append("%Categories  : " + cats)
        vim.current.buffer.append("%Tags  : " + tags)
    vim.current.buffer.append(META_DATA_END + "\n")
    # close html comment tag.
    # append blank line between metadata and content
    vim.current.buffer.append("\n")
    
def blog_open_post(id):
    global localtempdir,handler,blog_login_success

    if not blog_login_success:
        blog_init()
        # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.
    try:
        # use wp.getPost using the XMLRPC library. 
        post = handler.getPost(0, blog_username, blog_password, id)
        # post is a dictionary with fields like 'post_title','post_content'
        blog_edit_on()
        # I don't know what this function does as yet, but it seems to enable editing the file by unmapping some keys.
        vim.command("set syntax="+VIMSYNTAX)
        vim.command("set filetype="+VIMFILETYPE)
        # this sets the filetype so that syntax highlighting is set correctly
    
        vim.command('set nomodified')
        # this sets the current buffer to "not as yet modified", even though the script has made changes to it.
        #vim.command('set textwidth=0')
    
        del vim.current.buffer[:]
        if enable_terms:
            write_post_metadata(strid=str(id),title=post['post_title'],cats=blog_get_cats(),tags=blog_get_meta())
        else:
            write_post_metadata(strid=str(id),title=post['post_title'],cats='',tags='')

        # automatically cursor position is now after the first line.
        content = convert_html_markdown((post['post_content']),from_format=blog_post_format,to_format='markdown')
    
        for line in content.split('\n'):
          vim.current.buffer.append(line)
          # append the lines from the tex files into current buffer
    
        # find out where the text starts, and put the cursor there. There is a check to see that it doesn't overflow the buffer in seek_content_beginning()
        text_start = seek_content_beginning()
        # move to the next line
        vim.current.window.cursor = (text_start, 0)
        #vim.current.window.cursor = (text_start+1, 0)
    except:
        sys.stderr.write("An error has occured in the python function blog_open_post")
        traceback.print_exc(file=sys.stdout)

#def blog_get_meta():

def seek_content_beginning():
    # this is an important bit of code that seeks the start of the content
    text_start = 0
    found = False
    text_end = len(vim.current.buffer)
    while (not found) and text_start < text_end :
        # increment the counter until the % == Content tag is found.
        if vim.current.buffer[text_start] == META_DATA_END:
            found = True
        text_start +=1
    #endwhile
  
    # move to line after the content tag, so increment text_start
    # increment it only if not at end of buffer
    text_start = min(text_start + 1,text_end)
    return text_start
  
def blog_list_edit():
    # after listing posts, allow post selection
    global blog_login_sucess,handler
    if not blog_login_success:
        blog_init()
        # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.
    try:
        row,col = vim.current.window.cursor
        # get post id from current line
        id = vim.current.buffer[row-1].split()[0]
        blog_open_post(int(id))
    except:
        if dbg >= 1:
            sys.stderr.write("\nerror in blog_list_edit\n")
        else:
            pass
      # the traceback gives errors
      #traceback.print_exc(file=sys.stdout)

def set_post_type():
    # input post type. Usually set to page or post.
    global blog_post_type
    vimcmd = "input('Enter post type (page, post): ')"
    if dbg >= 1:
        print(vimcmd)
    blog_post_type=vim.eval(vimcmd)

def blog_list_posts():
    global handler, blog_login_success, from_vim, dbg

    if dbg >= 1:
        sys.stdout.write("blog_login_success is: " + str(blog_login_success) + "\n")
        sys.stdout.write("blog_username is: " + str(blog_username) + "\n")
        sys.stdout.write("blog_username is: " + str(blog_username) + "\n")
  
    if not blog_login_success:
        blog_init()
        # this will also set blog_login_success. hopefully you will be able to login.
    try:
        allposts = handler.getPosts(0,blog_username,blog_password,{'post_type':blog_post_type})

        size=len(allposts[0]['post_id'])
        # get length of postid for correct formatting
        if from_vim:
            del vim.current.buffer[:]
            vim.command("set syntax="+VIMSYNTAX)
            vim.current.buffer[0] = "%====== List of Posts ========="
            for p in allposts:
                #vim.current.buffer.append("".zfill(size-len(p['postid'])).replace("0", " ")+p["postid"]+"\t"+(p["title"]))
              vim.current.buffer.append("".zfill(size-len(p['post_id'])).replace("0", " ")+p["post_id"]+"\t"+p["post_title"])
              # do not allow editing
            vim.command('set nomodified')
            blog_edit_off()
            vim.current.window.cursor = (2, 0)
            if py3:
                vim.command('map <enter> :py3 blog_list_edit()<cr>')
            else:
                vim.command('map <enter> :py blog_list_edit()<cr>')
        else:
            for p in allposts:
                print("".zfill(size-len(p['post_id'])).replace("0", " ")+p["post_id"]+"\t"+p["post_title"])           
    except:
        sys.stderr.write("An error has occured in blog_list_posts")
        if dbg >= 1:
            traceback.print_exc(file=sys.stdout)

    return allposts

def convert_html_markdown(content,from_format='html',to_format='md'):
    fname_from = localtempdir + '/blog_post.' + from_format
    fname_to = localtempdir + '/blog_post.' + to_format
    if os.system('which pandoc >/dev/null 2>&1') == 0:
        with open(fname_from,'w') as f:
            # explicit file close commands need not be given
            f.write(content)
        out = subprocess.check_output(['pandoc','-f',from_format,'-t',to_format,'-o',fname_to,fname_from])
        if dbg >= 1:
            sys.stdout.write(out.decode())
        # now open the converted file
        with open(fname_to,'r') as f:
            output = f.read()
    else:
        # do not modify the content
        output = content
    # return content
    return output

def write_markdown_toc():
    # writes table of contents
    # perhaps modify for convenience, after adding TOC, move back to original location in file?
    global localtempdir, dbg
  
    try:
      # delete previous TOC
      # del_markdown_toc()
      # doctoc will auto refresh the TOC since it inserts tags automatically to demarcate the TOC section it generates.
  
      # seek beginning of blog post contents 
      text_start = seek_content_beginning() 
      # the content contains text_start to EOF
      content = vim.current.buffer[text_start:]
  
      # I could name the file using some sophisticated mechanism, but maybe not necessary
      tempfile = localtempdir + '/blogpost.md'
      f = open(tempfile,'w')
      # open temporary file in write mode
  
      # write content to file, we can iterate over the list content.
      for line in content:
      # write blog post contents to a file
        f.write(line + '\n')
  
      f.close()
      # close the file
  
      # run doctoc on the markdown file
      syscmd = 'doctoc ' + tempfile + ' 2>&1 > /tmp/doctout.out'
      # run the doctoc command on the file
      os.system(syscmd)
      # read the file into the buffer.
      
      # this will echo the whole tempfile, usually unnecessary
      #if dbg >= 1:
        #vim.command('echo tempfile')
  
      # clear old buffer
      del vim.current.buffer[text_start:]
      # do not need to append a blank line
  
      # start appending from markdown file with TOC
      f = open(tempfile,'r')
      # open the converted markdown file
      for line in f:
        vim.current.buffer.append(line)
      # move back to start of document. this is the line after the content tag
      vim.current.window.cursor = (text_start, 0)
  
      # delete the DOCTOC string inserted that says, "generated by DOCTOC"
      if dbg >= 1:
        sys.stdout.write("searching for doctoc string")
  
      line=0
      found_doctoc = False
      while (not found_doctoc) and line <= len(vim.current.buffer):
        # run loop while the DOCTOCSTRING IS NOT FOUND
        if vim.current.buffer[line].find(DOCTOCSTRING) != -1:
          # the function returns -1 if not found
          found_doctoc = True
          vim.current.buffer[line] = vim.current.buffer[line].replace(DOCTOCSTRING,'')
          if dbg >= 1:
            sys.stderr.write("line number = " + str(line))
            sys.stderr.write(DOCTOCSTRING + '\n')
            sys.stderr.write(vim.current.buffer[line].replace(DOCTOCSTRING,'') + '\n')
            sys.stderr.write("found doctoc string")
          # replace the doctocstring with nothing
        else:
            #otherwise increment line counter
            line = line + 1
       #endwhile 
  
      # print error message if not found doctoc string
      #if dbg and (not found_doctoc):
        #sys.stderr.write("did not find doctoc string")
  
    except:
        sys.stderr.write("Error occured in write_markdown_toc")
        traceback.print_exc(file=sys.stdout)

def del_markdown_toc():
    # the markdown toc is generated by doctoc. This deletes it if necessary. I now just refresh it using doctoc, a nice little javascript program
    global TOC_START_STRING, TOC_END_STRING
    try:
      # first look for Table of contents signature, TOC start
      found_start = False
      found_end = False
      bufend_line = len(vim.current.buffer) - 1 #last line of buffer, = lenght of buffer array - 1
  
      toc_start = 0
      while (not found_start) and toc_start <= bufend_line:
        # increment the counter until the Table of contents
        if vim.current.buffer[toc_start] == TOC_START_STRING:
          found_start = True
          #if found, will not increment loop and will end
        else:
          toc_start +=1
      #endwhile
  
      # find TOC end
      if found_start:
        toc_end = min(toc_start+1,bufend_line)
        while (not found_end) and toc_end <= bufend_line:
          # increment the counter until the Table of contents
          if vim.current.buffer[toc_end] == TOC_END_STRING:
            found_end = True
          else:
            toc_end +=1
  
      # if both tags are found, then toc_start <= bufend_line and toc_end <= bufend_line + 1
      # add extra +1 to toc_end because of python interval convention [a,b)
      if found_start and found_end:
        # if toc_end is at buffer end line + 1, make sure we dont go out of bounds
        #sys.stderr.write("toc_start " + str(toc_start) + "toc_end " + str(toc_end) )
        del vim.current.buffer[toc_start:min(toc_end,bufend_line)+1]
      else: 
        sys.stderr.write("Matching table of contents tags not found")
  
    except:
      sys.stderr.write("Error occured in del_markdown_toc")
      traceback.print_exc(file=sys.stdout)

