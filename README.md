# BCite
BCite is a bibliographic reference correction service that allows data curators to reconcile bibligoraphic data with existing citations available in OpenCitations and Crossref, clean bibliographic data, and generate new open citations as RDF data.

The tool includes a web interface for data entry and cleaning, a triplestore [Blazegraph](https://www.blazegraph.com), and an API for interacting with OpenCitations and Crossref.

## Requirements

* [python3](https://www.python.org/download/releases/3.0/?)
* [webpy](http://webpy.org/)

## Usage

* Clone or download the git repo.
* Run the triplestore launching the file `run-local.sh` included in the directory `triplestore/sh` - and stop it bu running `stop.sh`. The triplestore runs at port 9999.
* Run the web application by launching `python3 -m script.web.app 8000`. The BCite App runs at [http://localhost:8000](http://localhost:8000).

## Evaluation
To evaluate the precision of the tool, and the number of open citations created, the following data is used: [https://doi.org/10.6084/m9.figshare.6462443](https://doi.org/10.6084/m9.figshare.6462443). Results are outlined in the csv file.