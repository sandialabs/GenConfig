import getpass
from pathlib import Path
import pytest
import sys
import textwrap
from unittest.mock import patch

root_dir = (Path.cwd()/".."
            if (Path.cwd()/"conftest.py").exists()
            else Path.cwd())

sys.path.append(str(root_dir))
from configparserenhanced import ConfigParserEnhanced
from gen_config import GenConfig
import gen_config


###############################################################################
########################     Functionality     ################################
###############################################################################
def test_list_config_flags(capsys):
    # Just make sure the exception is raised with a small message match.
    # Checking that the correct config flags are displayed is tested in
    # test_unit_config_keyword_parser.
    with pytest.raises(SystemExit) as SE:
        gen_config.main([
            "--config-specs", "test-config-specs.ini",
            "--supported-config-flags", "test-supported-config-flags.ini",
            "--supported-systems", "test-supported-systems.ini",
            "--supported-envs", "test-supported-envs.ini",
            "--environment-specs", "test-environment-specs.ini",
            "--list-config-flags",
            "--force", "ats1"
        ])

    exc_msg, stderr = capsys.readouterr();

    assert str(SE.value) == str(0)


# Primarily to check a branch coverage
@pytest.mark.parametrize("test_from_main", [True, False])
@pytest.mark.parametrize("sys_name", ["ats1", "ats2"])
def test_list_configs_shows_correct_sections(sys_name, test_from_main, capsys):
    config_specs = ConfigParserEnhanced("test-config-specs.ini").configparserenhanceddata
    expected_configs = [_ for _ in config_specs.sections() if _.startswith(sys_name)]
    argv = [
        "--config-specs", "test-config-specs.ini",
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--list-configs",
        "--force", sys_name
    ]

    with pytest.raises(SystemExit):
        if test_from_main:
            gen_config.main(argv)
        else:
            gc = GenConfig(argv)
            gc.list_configs()

    exc_msg, stderr = capsys.readouterr();

    for config in expected_configs:
        assert f"- {config}" in exc_msg


@pytest.mark.parametrize("extra_args", [
    ["--list-configs"],
    ["--list-config-flags"],
    ["--cmake-fragment", "foo.cmake"],
    ["--cmake-fragment", "foo.cmake", "--list-configs"],
    ["--cmake-fragment", "foo.cmake", "--list-configs", "--list-config-flags"],
])
def test_output_load_env_args_only_correctly(extra_args):
    load_env_args_output_file = "load_env_args.out"
    argv = [
        "--config-specs", "test-config-specs.ini",
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--output-load-env-args-only",
    ]
    argv += extra_args
    argv += ["--force", "ats1_intel-hsw"]

    expected_load_env_args = [
        "--supported-systems", str(Path('test-supported-systems.ini').resolve()),
        "--supported-envs", str(Path('test-supported-envs.ini').resolve()),
        "--environment-specs", str(Path('test-environment-specs.ini').resolve()),
        "--force", "ats1_intel-hsw"
    ]
    expected_args_str = " ".join(expected_load_env_args)

    with pytest.raises(SystemExit):
        gc_args_str = gen_config.main(argv)
        assert gc_args_str == expected_args_str


@pytest.mark.parametrize("data", [
    {
        "build_name": "ats1_intel-hsw",
        "expected_complete_config": "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_serial_none"
    }
])
def test_complete_config_generated_correctly(data):
    gc = GenConfig([
        "--config-specs", "test-config-specs.ini",
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--force",
        data["build_name"]
    ])

    assert gc.complete_config == data["expected_complete_config"]
    # For the sake of branch coverage of an if statement in
    # the property complete_config, run this again...
    #
    #   # Will evaluate to False the second time through
    #   if not hasattr(self, "_complete_config"):
    #       # Do things here
    #
    assert gc.complete_config == data["expected_complete_config"]

@pytest.mark.parametrize("data", [
    {
        "build_name": "ats1_intel-hsw",
        "expected_args_str": '-DMPI_EXEC_NUMPROCS_FLAG:STRING="-p"'
    },
    {
        "build_name": "ats1_intel-hsw_sparc",
        "expected_args_str": ('-DMPI_EXEC_NUMPROCS_FLAG:STRING="-p" \\\n'
                     '    -DTPL_ENABLE_MPI:BOOL=ON')
    },
    {
        "build_name": "ats1_intel-hsw_empire_sparc",
        "expected_args_str": ('-DMPI_EXEC_NUMPROCS_FLAG:STRING="-p" \\\n'
                     '    -DTPL_ENABLE_MPI:BOOL=ON \\\n'
                     '    -DTrilinos_ENABLE_Panzer:BOOL=ON')
    },
])
def test_bash_cmake_flags_generated_correctly(data):
    user = getpass.getuser()
    gen_config.main([
        "--bash-cmake-args-location", f"/tmp/{user}/.bash_cmake_args",
        "--config-specs", "test-config-specs.ini",
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--force",
        data["build_name"]
    ])

    loc_file = Path(f"/tmp/{user}/.bash_cmake_args")
    assert loc_file.exists()
    with open(loc_file, "r") as F:
        bash_cmake_args = F.read()

    assert bash_cmake_args == data["expected_args_str"]

    loc_file.unlink()


@pytest.mark.parametrize("data", [
    {
        "build_name": "ats1_intel-hsw",
        "expected_fragment_contents": 'set(MPI_EXEC_NUMPROCS_FLAG -p CACHE STRING "from .ini configuration")'
    },
    {
        "build_name": "ats1_intel-hsw_sparc",
        "expected_fragment_contents": (
            'set(MPI_EXEC_NUMPROCS_FLAG -p CACHE STRING "from .ini configuration")\n'
            'set(TPL_ENABLE_MPI ON CACHE BOOL "from .ini configuration")'
        )
    },
    {
        "build_name": "ats1_intel-hsw_empire_sparc",
        "expected_fragment_contents": (
            'set(MPI_EXEC_NUMPROCS_FLAG -p CACHE STRING "from .ini configuration")\n'
            'set(TPL_ENABLE_MPI ON CACHE BOOL "from .ini configuration")\n'
            'set(Trilinos_ENABLE_Panzer ON CACHE BOOL "from .ini configuration")'
        )
    },
])
def test_cmake_fragment_file_stored_correctly(data):
    gen_config.main([
        "--config-specs", "test-config-specs.ini",
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--cmake-fragment", "test_fragment.cmake",
        "--force",
        data["build_name"]
    ])
    with open("test_fragment.cmake", "r") as F:
        test_fragment_contents = F.read()

    assert test_fragment_contents == data["expected_fragment_contents"]


@pytest.mark.parametrize("data", [
    {"--yes flag": False, "should_exit": False, "user_input": ["Y"]},
    {"--yes flag": False, "should_exit": False, "user_input": ["8", "y"]},
    {"--yes flag": True, "should_exit": False, "user_input": []},
    {"--yes flag": False, "should_exit": True, "user_input": ["N"]},
    {"--yes flag": False, "should_exit": True, "user_input": ["8", "n"]},
])
@patch("gen_config.input")
def test_existing_cmake_fragment_file_asks_user_for_overwrite(mock_input, data):
    argv = [
        "--config-specs", "test-config-specs.ini",
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--cmake-fragment", "test_fragment.cmake",
        "--force",
        "ats1_intel-hsw"
    ]
    if data["--yes flag"]:
        argv.insert(-1, "--yes")

    expected_fragment_contents = (
        'set(MPI_EXEC_NUMPROCS_FLAG -p CACHE STRING "from .ini configuration")'
    )
    Path("test_fragment.cmake").touch()

    mock_input.side_effect = data["user_input"]
    if data["should_exit"]:
        with pytest.raises(SystemExit):
            gen_config.main(argv)
    else:
        gen_config.main(argv)
        with open("test_fragment.cmake", "r") as F:
            test_fragment_contents = F.read()

        assert test_fragment_contents == expected_fragment_contents

    if not data["--yes flag"]:
        script_input_text = mock_input.call_args[0][0]
        if data["user_input"][0].lower() not in ["y", "n"]:
            assert "not recognized" in script_input_text
        else:
            assert "not recognized" not in script_input_text


###############################################################################
##########################     Validation     #################################
###############################################################################
# Build name validity
@pytest.mark.parametrize("data", [
    {
        "build_name": "rhel7_sems-gnu-7.2.0-serial_release-debug_shared_no-kokkos-arch_no-asan_no-complex_no-fpic_no-mpi_no-pt_no-rdc_no-uvm_deprecated-on_no-package-enable",
        "invalid_options": ["no-package-enable"],
    },
    {
        "build_name": "rhel7_sems-gnu-7.2.0-serial_release-debug_shared_no-kokkos-arch_no-asan_no-complex_no-fpic_no-mpi_no-pt_no-rdc_no-uvm_deprecated_no-package-enables",
        "invalid_options": ["deprecated"],
    },
    {
        "build_name": "rhel7_sems-gnu-7.2.0-serial_release-debug_shared_no-kokkos-arch_no-asan_no-complex_no-fpic_no-mpi_no-pt_no-rdc_no-uvm_deprecated-of_no-package-enables",
        "invalid_options": ["deprecated-of"],
    },
    {
        "build_name": "PR-10229-test_rhel7_sems-clang-10.0.0-openmpi-1.10.1-serial_release-debug_shared_no-kokkos-arch_no-asan_no-complex_no-fpic_mpi_no-pt_no-rdc_no-uvm_deprecated-on_no-package-enables-186",
        "invalid_options": ["PR-10229-test", "no-package-enables-186"],
    },
])
def test_invalid_option_in_build_name_raises(data):
    """
    Note: These tests derive from unexpected behavior encountered in the wild.
    Correct behavior is tested for here.
    """
    gc = GenConfig([
        "--config-specs", "test-config-specs-invalid-option-in-build-name-raises.ini",
        "--supported-config-flags", "test-supported-config-flags-invalid-option-in-build-name-raises.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--force", data["build_name"]
    ])

    with pytest.raises(ValueError) as excinfo:
        gc.complete_config

    exc_msg = excinfo.value.args[0]
    for opt in data["invalid_options"]:
        assert f"- {opt}" in exc_msg

# config_specs.ini and supported-systems.ini integration
# =======================
@pytest.mark.parametrize("data", [
    {"config_specs_filename": "test-config-specs.ini",
     "supported_systems_filename": "test-supported-systems.ini",
     "section_names": [],
     "raises": False},

    {"config_specs_filename": "test-config-specs-1-new-system-1-section.ini",
     "supported_systems_filename": "test-supported-systems.ini",
     "section_names": "dne8_cee-cuda-10.1.243-gnu-7.2.0-openmpi-4.0.3_mpi_serial_none",
     "raises": True},

    {"config_specs_filename": "test-config-specs-1-new-system-2-section.ini",
     "supported_systems_filename": "test-supported-systems.ini",
     "section_names": ["dne8_cee-cuda-10.1.243-gnu-7.2.0-openmpi-4.0.3_mpi_serial_none",
                     "dne8_cee-cuda-10.1.243-gnu-7.2.0-openmpi-4.0.3_mpi_serial_empire"],
     "raises": True},

    {"config_specs_filename": "test-config-specs-2-new-system-3-section.ini",
     "supported_systems_filename": "test-supported-systems.ini",
     "section_names": ["dne8_cee-cuda-10.1.243-gnu-7.2.0-openmpi-4.0.3_mpi_serial_none",
             "dne9_cee-cuda-10.1.243-gnu-7.2.0-openmpi-4.0.3_mpi_serial_none",
             "dne9_cee-cuda-10.1.243-gnu-7.2.0-openmpi-4.0.3_mpi_serial_empire"],
     "raises": True}
])
def test_supported_systems_missing_system_raises(data):

    run_common_supported_systems_validation_test(data["config_specs_filename"], data["supported_systems_filename"],
                                                 data["section_names"], data["raises"])

# Section Name Validation
# =======================
def run_common_config_specs_validation_test(test_ini_filename, section_names,
                                            should_raise, msg=None):
    gc = GenConfig([
        "--config-specs", test_ini_filename,
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--force",
        "ats1_env-name_mpi"
    ])


    if should_raise:
        with pytest.raises(ValueError) as excinfo:
            gc.validate_config_specs_ini()

        exc_msg = excinfo.value.args[0]
        msg_expected = (
            msg
            if msg is not None
            else get_expected_config_specs_exc_msg(section_names, test_ini_filename)
        )
        assert msg_expected in exc_msg


def get_expected_config_specs_exc_msg(section_names, test_ini_filename):
    formatted_section_name = "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_serial_sparc"
    msg_expected = textwrap.dedent(
        f"""
        |   ERROR:  The following section(s) in your config-specs.ini file
        |           should be formatted in the following manner to include only valid
        |           options and to match the order of supported flags/options in
        |           'test-supported-config-flags.ini':
        |
        |           -  {{current_section_name}}
        |           -> {{formatted_section_name}}
        |
        """
    ).strip()
    msg_expected += "\n"

    if type(section_names) == list:
        for section_name in section_names:
            msg_expected += (
                f"|           -  {section_name}\n"
                f"|           -> {formatted_section_name}\n|\n"
            )
    else:
        msg_expected += (
            f"|           -  {section_names}\n"
            f"|           -> {formatted_section_name}\n|\n"
        )

    msg_expected += f"|   Please correct these sections in '{test_ini_filename}'."

    return msg_expected


def run_common_supported_systems_validation_test(test_config_specs_file: str, test_supported_systems_file: str,
                                                 section_names, should_raise: bool):
    gc = GenConfig([
        "--config-specs", test_config_specs_file,
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", test_supported_systems_file,
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--force",
        "rhel7_cee-cuda-10.1.243-gnu-7.2.0-openmpi-4.0.3_mpi_serial_none"
    ])


    if should_raise:
        with pytest.raises(ValueError) as excinfo:
            gc.validate_config_specs_ini()

        exc_msg = excinfo.value.args[0]
        msg_expected = get_expected_supported_systems_exc_msg(section_names, test_supported_systems_file)
        assert msg_expected in exc_msg


def get_expected_supported_systems_exc_msg(section_names, test_supported_systems_filename):
    msg_expected = textwrap.dedent(
        f"""
        |   ERROR:  The following section(s) in your config-specs.ini file
        |           do not match any systems listed in
        |           '{test_supported_systems_filename}':
        |
        """
    ).strip()
    msg_expected += "\n"

    if type(section_names) == list:
        for section_name in section_names:
            msg_expected += (
                f"|           -  {section_name}\n"
            )
    else:
        msg_expected += (
            f"|           -  {section_names}\n"
        )

    msg_expected += f"|   Please update '{test_supported_systems_filename}'."

    return msg_expected


@pytest.mark.parametrize("data", [
    {
        "section_name":
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_serial_sparc",
        "should_raise": False
    },
    {
        "section_name":
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_serial_sparc",
        "should_raise": True
    },
    {
        "section_name":
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_sparc",
        "should_raise": True
    },
])
def test_section_without_options_specified_for_all_flags_raises(data):
    bad_config_specs = (
        f"[{data['section_name']}]\n"
        "opt-set-cmake-var CMAKE_BUILD_TYPE STRING : DEBUG\n"
    )
    test_ini_filename = "test_bad_config_specs_section_incorrect_order.ini"
    with open(test_ini_filename, "w") as F:
        F.write(bad_config_specs)

    run_common_config_specs_validation_test(test_ini_filename, data["section_name"], data["should_raise"])


@pytest.mark.parametrize("data", [
    {
        "section_name":
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_serial_sparc",
        "should_raise": False
    },
    {
        "section_name":
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_serial_mpi_sparc",
        "should_raise": True
    },
    {
        "section_name":
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_sparc_serial_mpi",
        "should_raise": True
    },
])
def test_section_with_incorrect_flag_order_raises(data):
    bad_config_specs = (
        f"[{data['section_name']}]\n"
        "opt-set-cmake-var CMAKE_BUILD_TYPE STRING : DEBUG\n"
    )
    test_ini_filename = "test_bad_config_specs_section_incorrect_order.ini"
    with open(test_ini_filename, "w") as F:
        F.write(bad_config_specs)

    run_common_config_specs_validation_test(test_ini_filename, data["section_name"], data["should_raise"])


@pytest.mark.parametrize("data", [
    {
        "section_name":
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_serial_sparc",
        "should_raise": False
    },
    {
        "section_name":
        ("ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_serial_sparc"
         "_not-an-option"),
        "should_raise": True
    },
])
def test_items_in_config_specs_sections_that_arent_options_raises(data):
    """
    Something like the folliwing in `config-specs.ini` should raise an
    exception::

        # config-specs.ini
        [ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_not-an-option_sparc]
        #                               invalid ---^___________^
    """
    bad_config_specs = (
        f"[{data['section_name']}]\n"
        "opt-set-cmake-var CMAKE_BUILD_TYPE STRING : DEBUG\n"
    )
    test_ini_filename = "test_bad_config_specs_section_item_not_an_option.ini"
    with open(test_ini_filename, "w") as F:
        F.write(bad_config_specs)

    run_common_config_specs_validation_test(
        test_ini_filename, data["section_name"], data["should_raise"],
        msg="The build name contains the following invalid options"
    )


def test_multiple_invalid_config_specs_sections_are_shown_in_one_err_msg():
    bad_section_names = [
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_serial_sparc",
        "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_sparc_serial",
    ]
    bad_config_specs = ""
    for sec_name in bad_section_names:
        bad_config_specs += (
            f"[{sec_name}]\n"
            "opt-set-cmake-var CMAKE_BUILD_TYPE STRING : DEBUG\n\n"
        )

    test_ini_filename = "test_config_specs_multiple_invalid_sections.ini"
    with open(test_ini_filename, "w") as F:
        F.write(bad_config_specs)

    should_raise = True
    run_common_config_specs_validation_test(test_ini_filename, bad_section_names, should_raise)

# Operation Validation
# ====================
@pytest.mark.parametrize("data", [
    {
        "operations": ["use"],
        "invalid": [],
        "should_raise": False
    },
    {
        "operations": ["use", "invalid-operation"],
        "invalid": ["invalid-operation"],
        "should_raise": True
    },
    {
        "operations": ["invalid-operation", "invalid-operation-2"],
        "invalid": ["invalid-operation", "invalid-operation-2"],
        "should_raise": True
    },
    {
        "operations": ["use", "invalidOperationNoDashes"],
        "invalid": ["invalidOperationNoDashes"],
        "should_raise": True
    },
])
def test_invalid_operations_raises(data):
    valid_section_name = "ats1_intel-19.0.4-mpich-7.7.15-hsw-openmp_mpi_serial_sparc"
    bad_config_specs = ("[ATS1]\n"
                        "opt-set-cmake-var CMake_Var STRING : ''\n\n"
                        f"[{valid_section_name}]\n")
    for operation in data["operations"]:
        bad_config_specs += ("use ATS1\n"
                             if operation == "use"
                             else f"{operation} params for op: here\n")

    test_ini_filename = "test_config_specs_invalid_operations.ini"
    with open(test_ini_filename, "w") as F:
        F.write(bad_config_specs)

    gc = GenConfig([
        "--config-specs", test_ini_filename,
        "--supported-config-flags", "test-supported-config-flags.ini",
        "--supported-systems", "test-supported-systems.ini",
        "--supported-envs", "test-supported-envs.ini",
        "--environment-specs", "test-environment-specs.ini",
        "--force",
        "ats1_any_build_name"
    ])


    if data["should_raise"]:
        with pytest.raises(ValueError):
            gc.validate_config_specs_ini_operations()
    else:
        gc.validate_config_specs_ini()
        # For the sake of branch coverage of an if statement in
        # validate_config_specs_ini, run this again...
        #
        #   # Will evaluate to False the second time through
        #   if self.set_program_options is None:
        #       self.load_set_program_options()
        #
        gc.validate_config_specs_ini()
