Extra tools left out of the `lint` extra:

`pylint`: slow and noisy

`coverage`: coverage is too bad to even bother putting this in CI

* `pylint` < `flake8`
	* some warnings (generally pylint ⊇ flake8)
	* line length
* `isort` < `flake8`
	* line length
	* ignored file list
* `coverage` < `flake8`
	* ignored file list
