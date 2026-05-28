class Drummer < Formula
  include Language::Python::Virtualenv

  desc "Local, standalone REST client — free alternative to Postman/Insomnia/Bruno"
  homepage "https://github.com/ceautery/drummer"

  # TODO: update url and sha256 when a GitHub release exists
  # Run `make dist` after tagging a release to generate the correct sha256.
  url "https://github.com/ceautery/drummer/releases/download/v0.1.0/drummer-0.1.0-py3-none-any.whl"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"

  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"drummer", "--version"
  end
end
