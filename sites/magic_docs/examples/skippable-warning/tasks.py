from magicinvoke import skippable

@skippable
def get_tool_output(input_file, output_file):
    output_file.write_bytes("written")

global_filenames = ("x", "y", "z")
@skippable
def unsafe_run_and_summarize(summary_output_path="x"):
    for filename in global_filenames:
        get_tool_output(filename, filename)
    summary_output_path.write_bytes("summary")
    print("Done running test and writing summary!")
