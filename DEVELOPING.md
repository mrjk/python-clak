# Developing notes

## POC Workflow

* Initial POC loop (when you don't know where to start)
    * Create file in lab/experiments1_NAME.py
        * Test and experiment code
    * Create file in LIB/NAME.py
        * Implement code from lab/experiment1_NAME.py
        * It will be production ready code
    * Create examples/example_101_NAME.py
        * Use code from LIB/NAME.py
        * Create a new example to illustrate the feature
    * Loop back to first item for next feature

* Getting out of POC (when you feel proud of LIB content)
    * Generate tests
        * Use AI to generate use cases tests from examples/ dir
        * Use AI to generate unit tests from LIB/ dir
        * Use AI to generate integration tests from LIB/ dir
        * Use AI to test and validate all examples

    * Generate examples
        * Just update them and make them easy to read and follow


    * Generate documentation
        * Create a doc/ dir
            * Configure documentation engine (like sphinx or mkdocs)
            * Tune the doc, style and design
        * From examples, ask AI to generate comprehensive tutorial
            * It bring the user the easily learn how to use the project
            * Should ends in doc/guide/NAME.md
        * From LIB, ask AI to generate technical documentation
            * It bring the user a technical documentation of the implementation
            * Should ends in doc/docs/NAME.md
        * Generate docstring
            * Generate documentation of project python API via documentation tools (like sphinx or mkdocs)
        * Integrate examples into documentation
            * Use jupyter notebook and md export to generate exports
            * Idea: keep docs as jupyter-parsable `.py` files (guides and examples)
              that include assertions, so the documentation pipeline both
              renders and validates them (served locally via `jupyter lab`)
        * Integrate project docs, such as license, readme, changelog, etc.

    * Integrate Taskfile
        * Create a taskfile.yaml file
        * Integrate tests
        * Integrate documentation generation and release
        * Integrate examples
        * All project tasks

    * Add more CI process in Taskfile
        * Add linting fix/check
        * Any automatic error tools
        * Code coverage

    * Integrate CI
        * Create a .github/workflows/main.yaml file
        * Forward all commands to Taskfile if possible
        * Configure and test external registries (pypi, docker, etc.)
        * Common:
            * Test and validate code
            * Push to external registries
            * Build and publish documentation
            * More ...


* Prepare release

    * Push on remote, validate CI works correctly
    * Run all tests again:
        * Tag a version 0.0.1a
        * Push on remote, test end to end the deployment solution
    * If good, tag a stable version, and process again



## First Release

This is more common, you can follow the best industry wide standard you prefers.

