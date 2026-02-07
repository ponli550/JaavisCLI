class Jaavis < Formula
  desc "One-Army AI Orchestrator & Skill Library"
  homepage "https://github.com/ponli550/JaavisCLI"
  url "https://github.com/ponli550/JaavisCLI/archive/refs/tags/v1.0.12.tar.gz"
  sha256 "031bf6c4a7d99b1c63a5bca87edb96812deb520f4c5583d6c185023d3e5d3550"
  license "MIT"

  depends_on "python@3.11"
  depends_on "git"

  def install
    # Install core script
    bin.install "jaavis_core.py" => "jaavis"

    # Install support files
    pkgshare.install "logo.md"
    pkgshare.install "jaavis_tui.py"
    pkgshare.install "jaavis_renderer.py"
  end

  def post_install
    # Initialize config if not exists
    # Note: Homebrew runs this as the user, but we should be careful with $HOME access
  end

  test do
    system "#{bin}/jaavis", "--help"
  end
end
