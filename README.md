# ftsgen - Family Tree Site Generator

Extract data from a family tree database/file and generate JSON files for displaying in a simple website. Supports extracting data from a Gramps XML export or a Family Tree Builder v8+ database (an SQLite database file with a ".ftb" extension).

Example commands to extract & generate JSON data:
```console
# generate JSON from Gramps XML export file
time ./extract.py --format gxml /path/to/data/family-extract-xml.gramps

# generate JSON from FTB database file
time ./extract.py --format ftb /path/to/data/family-database.ftb
```

Test and view website:
```
# move generated files into website directory
mkdir public/json
mv generated-data/* public/json/

# locally serve website for testing
cd public && python3 -m http.server
```

## Setup dev environment

Install poetry:
```console
curl -sSL https://install.python-poetry.org | python3 -
```

Install required python packages and activate virtual environment:
```console
poetry shell
poetry install
```
