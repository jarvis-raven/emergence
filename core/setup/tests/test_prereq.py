#!/usr/bin/env python3
"""Unit tests for prerequisite check module.

Uses unittest (stdlib only) to verify all check functions work correctly.
All subprocess calls are mocked to avoid requiring specific versions installed.
"""

import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

# Adjust path to import prereq module
sys.path.insert(0, str(Path(__file__).parent.parent))

from prereq import (
    check_node_version,
    check_ollama_installed,
    check_ollama_model,
    check_openclaw_gateway,
    check_python_version,
    detect_platform,
    offer_ollama_install,
    pull_ollama_model,
    run_ollama_install,
    run_check_json,
    run_prerequisite_check,
    _parse_node_version,
    _get_openclaw_port,
    DEFAULT_OPENCLAW_PORT,
    DEFAULT_OLLAMA_MODEL,
)


class TestNodeVersionParsing(unittest.TestCase):
    """Test Node.js version string parsing."""
    
    def test_parse_v_prefixed_version(self):
        """Parse version with v prefix like v18.19.0."""
        self.assertEqual(_parse_node_version("v18.19.0"), 18)
    
    def test_parse_plain_version(self):
        """Parse version without v prefix like 20.0.0."""
        self.assertEqual(_parse_node_version("20.0.0"), 20)
    
    def test_parse_with_whitespace(self):
        """Parse version with surrounding whitespace."""
        self.assertEqual(_parse_node_version("  v18.19.0\n"), 18)
    
    def test_parse_old_version(self):
        """Parse old Node version (16.x)."""
        self.assertEqual(_parse_node_version("v16.20.0"), 16)
    
    def test_parse_new_version(self):
        """Parse newer Node version (22.x)."""
        self.assertEqual(_parse_node_version("v22.5.1"), 22)


class TestPythonVersionCheck(unittest.TestCase):
    """Test Python version check."""
    
    def test_python_version_passes(self):
        """Python version check should pass on 3.9+."""
        ok, msg = check_python_version()
        # This test runs on the actual Python version
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)
        
        # On Python 3.9+, should pass
        if sys.version_info >= (3, 9):
            self.assertTrue(ok)
            self.assertIn("Python", msg)
            self.assertIn("✓", msg)


class TestNodeVersionCheck(unittest.TestCase):
    """Test Node.js version check with mocked subprocess."""
    
    @patch('prereq.subprocess.run')
    def test_node_check_success(self, mock_run):
        """Node 18+ should pass."""
        mock_run.return_value = Mock(returncode=0, stdout="v18.19.0\n", stderr="")
        
        ok, msg = check_node_version()
        
        self.assertTrue(ok)
        self.assertIn("18.19.0", msg)
        self.assertIn("✓", msg)
    
    @patch('prereq.subprocess.run')
    def test_node_check_too_old(self, mock_run):
        """Node 16 should fail."""
        mock_run.return_value = Mock(returncode=0, stdout="v16.20.0\n", stderr="")
        
        ok, msg = check_node_version()
        
        self.assertFalse(ok)
        self.assertIn("16.20.0", msg)
    
    @patch('prereq.subprocess.run')
    def test_node_check_not_found(self, mock_run):
        """Missing Node should fail with clear message."""
        mock_run.side_effect = FileNotFoundError()
        
        ok, msg = check_node_version()
        
        self.assertFalse(ok)
        self.assertIn("not found", msg.lower())
    
    @patch('prereq.subprocess.run')
    def test_node_check_timeout(self, mock_run):
        """Timeout should be handled gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired("node", 5)
        
        ok, msg = check_node_version()
        
        self.assertFalse(ok)
        self.assertIn("timed out", msg.lower())
    
    @patch('prereq.subprocess.run')
    def test_node_check_v20_passes(self, mock_run):
        """Node 20+ should pass."""
        mock_run.return_value = Mock(returncode=0, stdout="v20.11.0\n", stderr="")
        
        ok, msg = check_node_version()
        
        self.assertTrue(ok)
        self.assertIn("20.11.0", msg)


class TestOpenClawGatewayCheck(unittest.TestCase):
    """Test OpenClaw gateway health check."""
    
    @patch('prereq.http.client.HTTPConnection')
    def test_gateway_running(self, mock_conn_class):
        """Gateway returning 200 should pass."""
        mock_conn = Mock()
        mock_conn_class.return_value = mock_conn
        mock_response = Mock()
        mock_response.status = 200
        mock_conn.getresponse.return_value = mock_response
        
        ok, msg = check_openclaw_gateway()
        
        self.assertTrue(ok)
        self.assertIn("running", msg.lower())
        self.assertIn("✓", msg)
    
    @patch('prereq.http.client.HTTPConnection')
    def test_gateway_wrong_status(self, mock_conn_class):
        """Gateway returning non-200 should fail."""
        mock_conn = Mock()
        mock_conn_class.return_value = mock_conn
        mock_response = Mock()
        mock_response.status = 503
        mock_conn.getresponse.return_value = mock_response
        
        ok, msg = check_openclaw_gateway()
        
        self.assertFalse(ok)
        self.assertIn("503", msg)
    
    @patch('prereq.http.client.HTTPConnection')
    def test_gateway_connection_refused(self, mock_conn_class):
        """Connection refused should fail with clear message."""
        mock_conn = Mock()
        mock_conn_class.return_value = mock_conn
        mock_conn.request.side_effect = ConnectionRefusedError()
        
        ok, msg = check_openclaw_gateway()
        
        self.assertFalse(ok)
        self.assertIn("not running", msg.lower())
    
    @patch('prereq.http.client.HTTPConnection')
    def test_gateway_timeout(self, mock_conn_class):
        """Socket timeout should be handled."""
        import socket
        mock_conn = Mock()
        mock_conn_class.return_value = mock_conn
        mock_conn.request.side_effect = socket.timeout()
        
        ok, msg = check_openclaw_gateway()
        
        self.assertFalse(ok)
        self.assertIn("timed out", msg.lower())


class TestOllamaInstalledCheck(unittest.TestCase):
    """Test Ollama installation check."""
    
    @patch('prereq.subprocess.run')
    def test_ollama_installed(self, mock_run):
        """Ollama --version returning 0 should pass."""
        mock_run.return_value = Mock(
            returncode=0, 
            stdout="ollama version 0.1.24\n", 
            stderr=""
        )
        
        ok, msg = check_ollama_installed()
        
        self.assertTrue(ok)
        self.assertIn("0.1.24", msg)
        self.assertIn("✓", msg)
    
    @patch('prereq.subprocess.run')
    def test_ollama_not_installed(self, mock_run):
        """Missing Ollama should fail."""
        mock_run.side_effect = FileNotFoundError()
        
        ok, msg = check_ollama_installed()
        
        self.assertFalse(ok)
        self.assertIn("not installed", msg.lower())
    
    @patch('prereq.subprocess.run')
    def test_ollama_timeout(self, mock_run):
        """Timeout should be handled."""
        mock_run.side_effect = subprocess.TimeoutExpired("ollama", 5)
        
        ok, msg = check_ollama_installed()
        
        self.assertFalse(ok)
        self.assertIn("timed out", msg.lower())


class TestOllamaModelCheck(unittest.TestCase):
    """Test Ollama model availability check."""
    
    @patch('prereq.subprocess.run')
    def test_model_available(self, mock_run):
        """Model in list should pass."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="NAME\tID\tSIZE\tMODIFIED\nnomic-embed-text:latest\t1234\t274 MB\t2 weeks ago\n",
            stderr=""
        )
        
        ok, msg = check_ollama_model("nomic-embed-text")
        
        self.assertTrue(ok)
        self.assertIn("available", msg.lower())
        self.assertIn("✓", msg)
    
    @patch('prereq.subprocess.run')
    def test_model_not_available(self, mock_run):
        """Model not in list should fail."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="NAME\tID\tSIZE\tMODIFIED\nllama2:latest\t5678\t3.8 GB\t1 week ago\n",
            stderr=""
        )
        
        ok, msg = check_ollama_model("nomic-embed-text")
        
        self.assertFalse(ok)
        self.assertIn("not pulled", msg.lower())
    
    @patch('prereq.subprocess.run')
    def test_empty_model_list(self, mock_run):
        """Empty model list should fail."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="NAME\tID\tSIZE\tMODIFIED",
            stderr=""
        )
        
        ok, msg = check_ollama_model("nomic-embed-text")
        
        self.assertFalse(ok)
        self.assertIn("not pulled", msg.lower())
    
    @patch('prereq.subprocess.run')
    def test_ollama_list_fails(self, mock_run):
        """ollama list returning error should fail."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: could not connect to server"
        )
        
        ok, msg = check_ollama_model("nomic-embed-text")
        
        self.assertFalse(ok)
        self.assertIn("could not list", msg.lower())
    
    @patch('prereq.subprocess.run')
    def test_ollama_not_installed_for_model_check(self, mock_run):
        """Missing Ollama during model check should fail."""
        mock_run.side_effect = FileNotFoundError()
        
        ok, msg = check_ollama_model("nomic-embed-text")
        
        self.assertFalse(ok)
        self.assertIn("not installed", msg.lower())


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection."""
    
    @patch('prereq.platform.system')
    def test_detect_macos(self, mock_system):
        """Darwin should return macos."""
        mock_system.return_value = "Darwin"
        
        result = detect_platform()
        
        self.assertEqual(result, "macos")
    
    @patch('prereq.platform.system')
    def test_detect_linux(self, mock_system):
        """Linux should return linux."""
        mock_system.return_value = "Linux"
        
        result = detect_platform()
        
        self.assertEqual(result, "linux")
    
    @patch('prereq.platform.system')
    def test_detect_unknown(self, mock_system):
        """Unknown systems should return unknown."""
        mock_system.return_value = "Windows"
        
        result = detect_platform()
        
        self.assertEqual(result, "unknown")
    
    def test_detect_returns_valid_value(self):
        """Detection should always return a valid platform string."""
        result = detect_platform()
        
        self.assertIn(result, ("macos", "linux", "unknown"))


class TestOpenClawPortConfiguration(unittest.TestCase):
    """Test OpenClaw gateway port configuration."""
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('prereq.Path.exists')
    def test_default_port(self, mock_exists):
        """Should default to 6969 when no config exists."""
        mock_exists.return_value = False
        
        port = _get_openclaw_port()
        
        self.assertEqual(port, DEFAULT_OPENCLAW_PORT)
    
    @patch.dict('os.environ', {'OPENCLAW_GATEWAY_PORT': '8080'})
    @patch('prereq.Path.exists')
    def test_env_var_port(self, mock_exists):
        """Should use OPENCLAW_GATEWAY_PORT env var."""
        mock_exists.return_value = False
        
        port = _get_openclaw_port()
        
        self.assertEqual(port, 8080)
    
    @patch.dict('os.environ', {'OPENCLAW_GATEWAY_PORT': 'invalid'})
    @patch('prereq.Path.exists')
    def test_env_var_invalid_uses_default(self, mock_exists):
        """Invalid env var should fall back to default."""
        mock_exists.return_value = False
        
        port = _get_openclaw_port()
        
        self.assertEqual(port, DEFAULT_OPENCLAW_PORT)
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('prereq._read_emergence_config')
    def test_config_file_port(self, mock_read_config):
        """Should read port from emergence.json."""
        mock_read_config.return_value = {"openclaw": {"port": 7070}}
        
        port = _get_openclaw_port()
        
        self.assertEqual(port, 7070)


class TestInstallationHelpers(unittest.TestCase):
    """Test installation helper functions."""
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_offer_macos_install(self, mock_stdout):
        """Should print brew instructions for macOS."""
        offer_ollama_install("macos")
        
        output = mock_stdout.getvalue()
        self.assertIn("brew install ollama", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_offer_linux_install(self, mock_stdout):
        """Should print curl instructions for Linux."""
        offer_ollama_install("linux")
        
        output = mock_stdout.getvalue()
        self.assertIn("curl", output)
        self.assertIn("install.sh", output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_offer_unknown_install(self, mock_stdout):
        """Should print generic instructions for unknown."""
        offer_ollama_install("unknown")
        
        output = mock_stdout.getvalue()
        self.assertIn("ollama.com/download", output)
    
    @patch('prereq.subprocess.run')
    def test_run_macos_install_success(self, mock_run):
        """Successful brew install should return True."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        result = run_ollama_install("macos")
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["brew", "install", "ollama"],
            capture_output=True,
            text=True,
            timeout=120
        )
    
    @patch('prereq.subprocess.run')
    def test_run_macos_install_failure(self, mock_run):
        """Failed brew install should return False."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="brew error")
        
        result = run_ollama_install("macos")
        
        self.assertFalse(result)
    
    @patch('prereq.subprocess.run')
    def test_run_linux_install_success(self, mock_run):
        """Successful curl install should return True."""
        mock_run.return_value = Mock(returncode=0, stdout="Installed successfully", stderr="")
        
        result = run_ollama_install("linux")
        
        self.assertTrue(result)
    
    @patch('prereq.subprocess.run')
    def test_run_linux_install_failure(self, mock_run):
        """Failed curl install should return False."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="curl error")
        
        result = run_ollama_install("linux")
        
        self.assertFalse(result)
    
    @patch('prereq.subprocess.run')
    def test_pull_model_success(self, mock_run):
        """Successful model pull should return True."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        result = pull_ollama_model("nomic-embed-text")
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["ollama", "pull", "nomic-embed-text"],
            capture_output=True,
            text=True,
            timeout=600
        )
    
    @patch('prereq.subprocess.run')
    def test_pull_model_failure(self, mock_run):
        """Failed model pull should return False."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="pull failed")
        
        result = pull_ollama_model("nomic-embed-text")
        
        self.assertFalse(result)


class TestJsonOutput(unittest.TestCase):
    """Test JSON output format."""
    
    @patch('prereq.check_python_version')
    @patch('prereq.check_node_version')
    @patch('prereq.check_openclaw_gateway')
    @patch('prereq.check_ollama_installed')
    @patch('prereq.check_ollama_model')
    @patch('prereq.detect_platform')
    def test_json_structure_all_pass(
        self, mock_platform, mock_model, mock_ollama,
        mock_gateway, mock_node, mock_python
    ):
        """JSON should have expected structure when all pass."""
        mock_python.return_value = (True, "Python 3.11 ✓")
        mock_node.return_value = (True, "Node 18 ✓")
        mock_gateway.return_value = (True, "Gateway ✓")
        mock_ollama.return_value = (True, "Ollama ✓")
        mock_model.return_value = (True, "Model ✓")
        mock_platform.return_value = "macos"
        
        results = run_check_json()
        
        self.assertIn("hard_deps_ok", results)
        self.assertIn("soft_deps_ok", results)
        self.assertIn("checks", results)
        self.assertIn("platform", results)
        self.assertTrue(results["hard_deps_ok"])
        self.assertTrue(results["soft_deps_ok"])
        self.assertEqual(results["platform"], "macos")
    
    @patch('prereq.check_python_version')
    @patch('prereq.check_node_version')
    @patch('prereq.check_openclaw_gateway')
    @patch('prereq.check_ollama_installed')
    def test_json_hard_deps_fail(
        self, mock_ollama, mock_gateway, mock_node, mock_python
    ):
        """JSON should show hard_deps_ok=False when Python fails."""
        mock_python.return_value = (False, "Python too old")
        mock_node.return_value = (True, "Node ✓")
        mock_gateway.return_value = (True, "Gateway ✓")
        mock_ollama.return_value = (True, "Ollama ✓")
        
        results = run_check_json()
        
        self.assertFalse(results["hard_deps_ok"])
        self.assertIn("python", results["checks"])
        self.assertFalse(results["checks"]["python"]["ok"])


class TestIntegration(unittest.TestCase):
    """Integration tests for the full check workflow."""
    
    @patch('prereq.check_python_version')
    @patch('prereq.check_node_version')
    @patch('prereq.check_openclaw_gateway')
    @patch('prereq.check_ollama_installed')
    @patch('prereq.check_ollama_model')
    @patch('prereq.detect_platform')
    def test_all_deps_satisfied(
        self, mock_platform, mock_model, mock_ollama,
        mock_gateway, mock_node, mock_python
    ):
        """All deps satisfied should return 0."""
        mock_python.return_value = (True, "Python 3.11 ✓")
        mock_node.return_value = (True, "Node 18 ✓")
        mock_gateway.return_value = (True, "Gateway ✓")
        mock_ollama.return_value = (True, "Ollama ✓")
        mock_model.return_value = (True, "Model ✓")
        mock_platform.return_value = "macos"
        
        result = run_prerequisite_check(auto_fix=False)
        
        self.assertEqual(result, 0)
    
    @patch('prereq.check_python_version')
    @patch('prereq.check_node_version')
    def test_python_too_old(self, mock_node, mock_python):
        """Python too old should return 1 immediately."""
        mock_python.return_value = (False, "Python 3.8 too old")
        
        result = run_prerequisite_check(auto_fix=False)
        
        self.assertEqual(result, 1)
        mock_node.assert_not_called()
    
    @patch('prereq.check_python_version')
    @patch('prereq.check_node_version')
    @patch('prereq.check_openclaw_gateway')
    @patch('prereq.check_ollama_installed')
    @patch('prereq.check_ollama_model')
    def test_node_missing(self, mock_model, mock_ollama, mock_gateway, mock_node, mock_python):
        """Missing Node should return 2 (soft dep warning, not blocking)."""
        mock_python.return_value = (True, "Python 3.11 ✓")
        mock_node.return_value = (False, "Node not found")
        mock_gateway.return_value = (True, "Gateway ✓")
        mock_ollama.return_value = (True, "Ollama installed")
        mock_model.return_value = (True, "Model available")
        
        result = run_prerequisite_check(auto_fix=False)
        
        self.assertEqual(result, 2)
    
    @patch('prereq.check_python_version')
    @patch('prereq.check_node_version')
    @patch('prereq.check_openclaw_gateway')
    @patch('prereq.check_ollama_installed')
    @patch('prereq.check_ollama_model')
    @patch('prereq.run_ollama_install')
    @patch('prereq.pull_ollama_model')
    def test_soft_deps_missing(
        self, mock_pull, mock_install, mock_model, mock_ollama,
        mock_gateway, mock_node, mock_python
    ):
        """Missing soft deps that fail to auto-fix should return 2."""
        mock_python.return_value = (True, "Python 3.11 ✓")
        mock_node.return_value = (True, "Node 18 ✓")
        mock_gateway.return_value = (True, "Gateway ✓")
        mock_ollama.return_value = (False, "Ollama not installed")
        mock_model.return_value = (False, "Model not pulled")
        mock_install.return_value = False  # Install fails
        mock_pull.return_value = False  # Pull fails
        
        # auto_fix=True to skip input prompts, but installs fail
        result = run_prerequisite_check(auto_fix=True)
        
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
