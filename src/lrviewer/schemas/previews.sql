CREATE TABLE StoreInfo ( version NOT NULL );
CREATE TABLE Pyramid (
		uuid NOT NULL,
		digest NOT NULL,
		colorProfile NOT NULL,
		fileTimeStamp,
		quality NOT NULL,
		croppedWidth NOT NULL,
		croppedHeight NOT NULL,
		pyramidFileTimeStamp,
		fingerprint,
		fromProxy
	);
CREATE TABLE PyramidLevel (
		uuid NOT NULL,
		digest NOT NULL,
		level NOT NULL,
		longDimension NOT NULL,
		lastAccess NOT NULL,
		width NOT NULL,
		height NOT NULL
	);
CREATE TABLE DeletedPyramid (
		uuid NOT NULL,
		digest NOT NULL,
		deletedTimeStamp NOT NULL
	);
CREATE TABLE ImageCacheEntry ( imageId NOT NULL, uuid NOT NULL, digest NOT NULL, orientation );
CREATE TABLE MotionPreview (
		uuid NOT NULL,
		digest NOT NULL,
		frameCount NOT NULL,
		longSide NOT NULL,
		fileTimeStamp NOT NULL,
		motionPreviewFileTimeStamp
	);
CREATE TABLE DeletedMotionPreview (
		uuid NOT NULL,
		digest NOT NULL,
		deletedTimeStamp NOT NULL
	);
CREATE TABLE MotionPreviewCacheEntry ( imageId PRIMARY KEY, uuid NOT NULL, digest NOT NULL );
CREATE TABLE FacePreview (
		uuid NOT NULL,
		digest NOT NULL,
		fileTimeStamp NOT NULL,
		facePreviewFileTimeStamp
	);
CREATE TABLE DeletedFacePreview (
		uuid NOT NULL,
		digest NOT NULL,
		deletedTimeStamp NOT NULL
	);
CREATE TABLE FacePreviewCacheEntry ( imageId PRIMARY KEY, uuid NOT NULL, digest NOT NULL );
CREATE INDEX index_lastAccess_longDimension ON PyramidLevel( lastAccess, longDimension );
CREATE INDEX deleted_timestamp ON DeletedPyramid( deletedTimeStamp, uuid, digest );
CREATE INDEX index_ImageCacheEntry_uuid_digest ON ImageCacheEntry ( uuid, digest, orientation );
CREATE INDEX index_DeletedMotionPreview_deletedTimeStamp ON DeletedMotionPreview( deletedTimeStamp, uuid, digest );
CREATE INDEX index_MotionPreviewCacheEntry_uuid_digest ON MotionPreviewCacheEntry ( uuid, digest );
CREATE INDEX index_DeletedFacePreview_deletedTimeStamp ON DeletedFacePreview( deletedTimeStamp, uuid, digest );
CREATE INDEX index_FacePreviewCacheEntry_uuid_digest ON FacePreviewCacheEntry ( uuid, digest );
CREATE UNIQUE INDEX index_uuid_digest ON Pyramid( uuid, digest );
CREATE UNIQUE INDEX index_uuid_digest_level ON PyramidLevel( uuid, digest, level );
CREATE UNIQUE INDEX deleted_uuid_digest ON DeletedPyramid( uuid, digest );
CREATE UNIQUE INDEX index_ImageCacheEntry_imageId ON ImageCacheEntry ( imageId );
CREATE UNIQUE INDEX index_DeletedMotionPreview_uuid_digest ON DeletedMotionPreview( uuid, digest );
CREATE UNIQUE INDEX index_DeletedFacePreview_uuid_digest ON DeletedFacePreview( uuid, digest );
CREATE TRIGGER trigger_delete_cache_entry
		AFTER DELETE ON Pyramid
		FOR EACH ROW
		BEGIN
			DELETE FROM ImageCacheEntry WHERE uuid = OLD.uuid AND digest = OLD.digest;
		END;
CREATE TRIGGER trigger_delete_motion_preview_cache_entry
		AFTER DELETE ON MotionPreview
		FOR EACH ROW
		BEGIN
			DELETE FROM MotionPreviewCacheEntry WHERE uuid = OLD.uuid AND digest = OLD.digest;
		END;
CREATE TRIGGER trigger_delete_face_preview_cache_entry
		AFTER DELETE ON FacePreview
		FOR EACH ROW
		BEGIN
			DELETE FROM FacePreviewCacheEntry WHERE uuid = OLD.uuid AND digest = OLD.digest;
		END;
