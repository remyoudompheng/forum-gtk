#!/bin/sh

rm -rf dist
mkdir -p dist/bin
#mkdir -p dist/lib/forum-gtk
mkdir -p dist/share/forum-gtk
mkdir -p dist/share/doc/forum-gtk

DISTFILES="ChangeLog flrnkill.example flrnrc.example History"

cp lib/*.py dist/share/forum-gtk
#for i in lib/*.py
#do
#    newi=`basename $i`
#    ln -s ../../share/forum-gtk/$newi dist/lib/forum-gtk/$newi
#done
cp $DISTFILES dist/share/doc/forum-gtk

cat > dist/bin/forum-gtk <<EOF
#!/bin/sh

PKGDIR=/usr/local/util/packages/forum-gtk
python2.5 \$PKGDIR/share/forum-gtk/main.py \$@
EOF

chmod 755 dist/share/forum-gtk/main.py dist/bin/forum-gtk
