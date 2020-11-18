
cd walkman-ui
npm run dist

cd ..

rm -rf web-files/dist/*
cp -rf walkman-ui/dist/* web-files/dist/
chmod -R 755 web-files/dist/*

