#!/usr/bin/env bash

# This script take a release tag that must have
# the format v\d+\.d+\.\d+(?:-(Beta|Alpha))
# Use perl to validate the input
tag_in=$1
version_tag=$(echo $tag_in | perl -ne 'if (m/^v(\d+)\.(\d+)\.(\d+)(?:-(Beta|Alpha))?$/){print $_}')
if [ -z "$version_tag" ]; then
  echo "*** The release.sh command takes a version tag as an argument."
  echo "    The version tag must match the regexp pattern: v\d+\.d+\.\d+(?:-(Beta|Alpha))"
  echo "    The version tag for {$tag_in} failed to match the pattern."
  exit 1
else
  echo ">>>> Preparing release: $version_tag"
fi

# Run flake8. Review syntax, code formatting, and complexity.
./flake8_src.sh
# Exit on failure
if [ $? != 0 ]; then
  echo "*** Not ready for release due to 'flake8' errors."
  exit 1
fi
echo ">>>> flake8 scans passed."

# Run all tests...
pytest src/test/ --cov=src.pypi_search --cov-report=html -v
if [ $? != 0 ]; then
  echo "*** Not ready for release due to 'pytest' errors."
  exit 1
fi
echo ">>>> pytest tests passed."

# Test the build...
uv build
if [ $? != 0 ]; then
  echo "*** Not ready for release due to 'uv build' errors."
  exit 1
else
  rm -fr dist
fi
echo ">>>> Build run-test passed."

## Test the Git-Workflow...
#act
#if [ $? != 0 ]; then
#  echo "*** Not ready for release due to 'act' errors."
#  exit 1
#fi
#echo ">>>> act git-workflows passed."
#
## Check for uncommited files.
#modified_files=$(git status --porcelain | grep -E '(^ M|M)')
#echo "--- Modified Files: [$modified_files]"
#if [ -n "$modified_files" ]; then
#  echo "*** Files have been modified."
#  echo "    Please commit modified files."
#  exit 1
#fi
#echo ">>>> All files committed (Nice!)."
#
## Check for unpushed commits
#unpushed_commits=$(git rev-list --count @{u}..HEAD 2>/dev/null)
#if [ "$unpushed_commits" -gt 0 ]; then
#  echo "*** There are unpushed: $unpushed_commits commit(s) have not been pushed."
#  echo "    Please push all commits before releasing."
#  exit 1
#fi
#echo ">>>> All commits pushed (Nice!)."

# Tag the release...
git tag -d ${version_tag}
git tag ${version_tag}
git push origin refs/tags/${version_tag} -f
echo ">>>> Version Release Tag: [$version_tag] applied to main heads local and remote."
echo "     Please perform Manual Release Actions on Github to Publish."
