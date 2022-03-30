Releease instructions
=========================

 # Don't forget to bump version / tag release in git
 cd ~/code/invokestuf/magicinvoke (on linux, doesn't work on windows)
conda create -n magicinvokereleasing python=3 pip
conda activate magicinvokereleasing
pip install invocations
pip install -e .

 7930  git diff
 7931  git log
 7934  invoke release.publish