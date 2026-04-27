class LateralusLang < Formula
  include Language::Python::Virtualenv

  desc "Lateralus programming language toolchain (compiler, LSP, formatter)"
  homepage "https://lateralus.dev"
  url "https://files.pythonhosted.org/packages/source/l/lateralus-lang/lateralus_lang-3.2.0.tar.gz"
  # Replace SHA after `brew fetch --build-from-source` produces the canonical hash:
  sha256 "a6a3e5da2ccfe2d8dc5d82e359484337ca4e9532dcf7631bee7f2a41a59dd5a0"
  license "MIT"
  head "https://github.com/bad-antics/lateralus-lang.git", branch: "main"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "lateralus-lang 3.2.0", shell_output("#{bin}/lateralus --version")
  end
end
