# pypi_search Prompts

## Update fetch_project_details()

Create a Step by Step Task List that is committed to memory, for executing the following request...
  - Update fetch_project_details()
    - fetch json data from url = f"https://pypi.org/pypi/{package_name}/json"
    - Return formatted text details consisting of elements that have been pulled from the returned json data. Example json data in the file pypi_pkg-example_json.json.
      Format a report in this order, formatted using markdown in this order.
      Then before returning a string, convert the string from markdown to terminal format using "rich".
      -  The data of interest from the json data returned...
        - classifiers (multiple lines)
        - Homepage
        - release_url
        - Bug Tracker
        - version
        - requires_python
        - python_required
        - description (Only output if --full-desc or -f option is given)
