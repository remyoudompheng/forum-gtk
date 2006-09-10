#!/bin/sh

rm -rf dist
mkdir -p dist/bin
mkdir -p dist/lib/forum-gtk
mkdir -p dist/share/forum-gtk
mkdir -p dist/share/doc/forum-gtk

cp src/lib/*.py dist/share/forum-gtk
for i in lib/*.py
do
    newi=`basename $i`
    ln -s ../../share/forum-gtk/$newi dist/lib/forum-gtk/$newi
done
cp src/* dist/share/doc/forum-gtk

cat > dist/bin/forum-gtk <<EOF
#!/bin/sh

PY_PKGDIR=/usr/local/util/lib/python2.4/site-packages
PKGDIR=/usr/local/util/packages/forum-gtk-devel

PYTHONPATH=\$PY_PKGDIR:\$PY_PKGDIR/gtk-2.0
python2.4 \$PKGDIR/share/forum-gtk/main.py \$@
EOF

chmod 755 dist/share/forum-gtk/main.py dist/bin/forum-gtk
