type GalleryEntity = Record<string, unknown>

export const savedGalleryImagesFromEntities = (entities: GalleryEntity[]) =>
  entities
    .filter((entity) => entity.image_locked && (entity.locked_image_url || entity.image_url))
    .map((entity) => ({
      id: entity.id,
      url: entity.locked_image_url || entity.image_url,
      path: entity.locked_image_url || entity.image_url,
      name: entity.name || '已保存图片',
      entity_name: entity.name,
      entity_id: entity.id,
    }))
