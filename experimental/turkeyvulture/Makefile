.PHONY: build

all: clean build



clean:
	rm -f build/templates.js
	rm -rf build/index
	rm -rf ../../site/media/js/turkeyvulture

build:
	python js.py > build/templates.js
	mkdir -p build/index
	python build_index.py all
	mkdir -p ../../site/media/js/turkeyvulture/build
	cp -R build/index ../../site/media/js/turkeyvulture/build
	cp -R build/assets/* ../../site/media/js/turkeyvulture/