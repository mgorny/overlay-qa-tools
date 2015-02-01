#!/bin/bash

set -e -x

jobs=24
repos=( $(portageq get_repos /) )
out=output/egencache

mkdir -p "${out}"

for r in "${repos[@]}"; do
	echo "*** Scanning repository ${r} ***" >&2

	egencache --update --repo="${r}" --jobs="${jobs}" \
		|& tee "${out}/${r}.txt" || :
done

exit 0
