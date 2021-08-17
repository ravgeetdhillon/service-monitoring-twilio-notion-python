freeze: 
	pip freeze | grep -v "pkg_resources" > requirements-dev.txt
	pipreqs . --savepath requirements.txt
