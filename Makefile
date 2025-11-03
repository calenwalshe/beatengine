.PHONY: dist bootstrap clean-release

RELEASE_DIR := release
ARCHIVE := $(RELEASE_DIR)/techno_engine.tgz
CHECKSUM := $(RELEASE_DIR)/checksums.txt
REPO := mltechno/techno_rhythm_engine

$(RELEASE_DIR):
	mkdir -p $(RELEASE_DIR)

dist: $(RELEASE_DIR)
	git archive --format=tar.gz -o $(ARCHIVE) HEAD
	(cd $(RELEASE_DIR) && shasum -a 256 techno_engine.tgz > checksums.txt)

bootstrap:
	@echo "curl -fsSL https://raw.githubusercontent.com/$(REPO)/main/scripts/bootstrap.sh | bash"

clean-release:
	rm -rf $(RELEASE_DIR)
