CREATE TABLE StoreInfo ( version NOT NULL );
CREATE TABLE RootPixels (
		uuid NOT NULL,
		digest NOT NULL,
		colorProfile NOT NULL,
		croppedWidth NOT NULL,
		croppedHeight NOT NULL,
		quality NOT NULL,
		jpegData NOT NULL
	);
CREATE UNIQUE INDEX index_uuid_digest ON RootPixels( uuid, digest );
