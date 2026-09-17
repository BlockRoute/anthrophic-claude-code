import os, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestEndToEnd(unittest.TestCase):
    """Runs the real ingest -> trades -> prices -> pump -> backtest path."""

    def test_demo_pipeline_recovers_ground_truth(self):
        proc = subprocess.run(
            [sys.executable, "scripts/demo.py", "--tokens", "30",
             "--pump-prob", "0.6", "--seed", "11"],
            cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        for section in ("TRADER PROFILE", "POST-SELL CONTINUATION",
                        "COPY-TRADING BACKTEST", "self-check"):
            self.assertIn(section, out)
        for model in ("mirror", "hold", "scale_out"):
            self.assertIn(model, out)

        # The >=+25% tier filters out decay noise, so it should land close to
        # the configured ground-truth pump rate.
        # row format: ">= +25%   <paper%>   <ci>   <achievable%>   <n>"
        line = [l for l in out.splitlines()
                if l.strip().startswith(">= +25%")][-1]
        recovered = float(line.split()[2].rstrip("%"))
        self.assertGreater(recovered, 35.0, f"recovered {recovered}%")
        self.assertLess(recovered, 85.0, f"recovered {recovered}%")

    def test_cli_help(self):
        proc = subprocess.run([sys.executable, "-m", "hoodtrack", "--help"],
                              cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--participation", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
