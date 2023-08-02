#!/bin/bash

# Set username and email
git config --global user.email "padillacoreanolab@gmail.com"
git config --global user.name "PadillaCoreanoLabGeneral"

# Clone the repository
# git clone https://github.com/padillacoreanolab/pc_mouseparty.git

# Change to the repository directory
# cd pc_mouseparty

# Checkout the master branch
# git checkout master

# Pull the latest changes
git pull

# Count the number of feature branches
feature_branches=$(git branch --all | grep -c "release")

# Count the number of hotfix branches
hotfix_branches=$(git branch --all | grep -c "release")

# Print the values of the variables using echo
echo "Feature branches: $feature_branches"
echo "Hotfix branches: $hotfix_branches"

# Update the version number using bump2version
command_minor="bump2version --allow-dirty minor:$feature_branches"
eval $command_minor
command_patch="bump2version --allow-dirty patch:$hotfix_branches"
eval $command_patch

# push tags to github and push final master version
git push --tags
git push origin master