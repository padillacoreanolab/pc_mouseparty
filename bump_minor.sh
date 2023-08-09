#!/bin/bash

# Set username and email
git config --global user.email "padillacoreanolab@gmail.com"
git config --global user.name "PadillaCoreanoLabGeneral"

# Pull the latest changes
git pull

# Update the version number using bump2version
command='bump2version --allow-dirty minor'
eval $command

# push tags to github and push final master version
git push --tags
git push origin master