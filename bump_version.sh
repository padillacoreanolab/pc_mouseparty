#!/bin/bash

# Set username and email
git config --global user.email "padillacoreanolab@gmail.com"
git config --global user.name "PadillaCoreanoLabGeneral"

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
command='bump2version --allow-dirty --replace "\d+\.\d+\.\d+" --new-version=0.$feature_branches.$hotfix_branches'
eval $command

# push tags to github and push final master version
git push --tags
git push origin master