# CollectionSpace Minibuild
 Use this project to configure Collectionspace 2.0

 Collectionspace 2.0 will need to be installed

 as well as [fabric](http://docs.fabfile.org/)

## Using fabric to deploy to a remote machine

*  First fork this project
*  then create a custom branch with `git checkout -b custom master`
*  follow 
[these instructions](http://wiki.collectionspace.org/display/UNRELEASED/Creating+your+new+tenant+using+the+mini-build) using this repo instead of the svn repo suggested in the instructions

*  Then edit the settings at the top of fabfile.py
*  use `fab -l` to see a list of commands to run 
*  push changes with `git push origin custom`
*  deploy with `fab deploy:ui`  or `fab deploy:application`


deploy task defaults to application

to reload the application configs locally run `fab hit_init:hosts=localhost`

schema changes will need to be deployed with 
[Services](http://github.com/collectionspace/services)



