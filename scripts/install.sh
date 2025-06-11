#!/usr/bin/env zsh

set -e
set -u

me=$(basename "$0")
REL_DIR=$0:P
DIR="$( cd "$( dirname "$REL_DIR" )" && pwd )";
cd "$DIR" 
cd "../" # go to parent of parent, which is project root.

echo "🚢 Start of '$me' (see: '$DIR/$me')"
echo "🚢 PWD: $PWD"

`git fetch --prune --tags`
function last_tag() {
    local out=`git tag --sort=taggerdate | tail -1`
    echo $out
}
echo "🚢 🏷️  Last tag: $(last_tag)"

# one liner from: https://stackoverflow.com/a/8653732
NEXT_TAG=$(echo $(last_tag) | awk -F. -v OFS=. 'NF==1{print ++$NF}; NF>1{if(length($NF+1)>length($NF))$(NF-1)++; $NF=sprintf("%0*d", length($NF), ($NF+1)%(10^length($NF))); print}')

OUTPUT_OF_BUILD=`sh $DIR/build_all.sh` || exit $?
echo "🚢  OUTPUT_OF_BUILD: $OUTPUT_OF_BUILD"

# `git tag $NEXT_TAG`
echo "🚢 🏷️ 📡 Pushing tag: $(NEXT_TAG), but only tag, not commit."
# `git push origin $NEXT_TAG`

echo "🚢  End of install script ✅"