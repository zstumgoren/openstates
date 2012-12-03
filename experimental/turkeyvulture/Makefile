.PHONY: build

all: clean build



clean:
	rm -f build/templates.js
	rm -rf build/index
	rm -rf ../../site/media/js/turkeyvulture

build:
	python js.py > build/templates.js
	python build_index.py ca
	for abbr in `ls ../../openstates`; do python build_index.py $abbr ; done
	mkdir -p build/index
	cp -R build ../../site/media/js/turkeyvulture