jobs = 6
repos = $(shell portageq get_repos /)
output_files = $(patsubst %,%.txt,$(repos))

all: $(output_files)

%.txt: %
	egencache --update --repo="$<" --jobs="$(jobs)" 2>&1 \
		| tee "$@" || :

clean:
	rm -f $(output_files)

.PHONY: all clean $(repos)
