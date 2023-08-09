#!/bin/bash

# Set username and email
git config --global user.email "padillacoreanolab@gmail.com"
git config --global user.name "PadillaCoreanoLabGeneral"

# Pull the latest changes
git pull

# Count the number of feature branches
feature_branches=$(git branch --all | grep -c "feature")

# Count the number of hotfix branches
hotfix_branches=$(git branch --all | grep -c "hotfix")

# Define verion numbers
major_num=0
# minor_num=$feature_branches
minor_num=0
# patch_num=$hotfix_branches
patch_num=0

# Update the version number using bump2version
command='bump2version --allow-dirty --replace "\d+\.\d+\.\d+" --new-version=$major_num.$minor_num.$patch_num patch'
eval $command

# push tags to github and push final master version
git push --tags
git push origin master