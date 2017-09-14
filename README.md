# vimpress

Essentially a fork of the original [vimscript](https://github.com/vim-scripts/Vimpress).
It used to store plaintext passwords and only worked with a single blog. 

Things it does a little differently

1.  It stores passwords in the system keyring. Works on linux and uses 
[secretstorage](http://pythonhosted.org/SecretStorage/).
1.  It uses the wordpress api, but I removed the tags functionality. If I really needed to
tag things I go into the wordpress site and do it. This is because the wordpress api is a bit of 
a pain to work with.


