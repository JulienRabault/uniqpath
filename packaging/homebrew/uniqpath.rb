# Homebrew formula for uniqpath.
#
# Lives in the tap repository JulienRabault/homebrew-tap, at Formula/uniqpath.rb.
# See ../README.md for how to create the tap and how the sha256 is filled in.
#
#   brew tap julienrabault/tap
#   brew install uniqpath

class Uniqpath < Formula
  include Language::Python::Virtualenv

  desc "Generate unique file or directory paths with flexible formatting"
  homepage "https://github.com/JulienRabault/uniqpath"
  url "https://files.pythonhosted.org/packages/source/u/uniqpath/uniqpath-0.2.0.tar.gz"
  sha256 "SHA256_OF_THE_SDIST"
  license "MIT"

  depends_on "python@3.13"

  # uniqpath has no runtime dependencies, so there are no `resource` blocks.

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_equal "demo.txt", shell_output("#{bin}/uniqpath demo.txt").strip

    touch "demo.txt"
    assert_equal "demo_1.txt", shell_output("#{bin}/uniqpath demo.txt").strip

    reserved = shell_output("#{bin}/uniqpath run --dir --reserve").strip
    assert_predicate testpath/reserved, :directory?
  end
end
