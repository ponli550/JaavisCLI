class Jaavis < Formula
  desc "One-Army AI Orchestrator & Skill Library"
  homepage "https://github.com/ponli550/JaavisCLI"
  url "https://github.com/ponli550/JaavisCLI/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"

  depends_on "python@3.11"
  depends_on "git"

  def install
    # Install core script
    bin.install "src/jaavis_core.py" => "jaavis"

    # Symlink face and library templates to the bin directory or shared folder
    # Homebrew formulae usually keep libraries in libexec or share
    pkgshare.install "src/logo.md"
    pkgshare.install "library"
  end

  def post_install
    # Initialize config if not exists
    # Note: Homebrew runs this as the user, but we should be careful with $HOME access
  end

  test do
    system "#{bin}/jaavis", "--help"
  end
end
