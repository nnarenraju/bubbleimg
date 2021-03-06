SELECT
  main.object_id, main.ra, main.dec, main.patch_id, main.tract, main.patch, main.patch_s, main.parent_id, main.deblend_nchild, main.detect_is_patch_inner, main.detect_is_tract_inner, main.detect_is_primary
FROM
  s16a_wide.forced AS main
  
WHERE
  (main.detect_is_tract_inner = 't' AND main.detect_is_patch_inner = 't' AND main.detect_is_primary ='t') AND (coneSearch(coord, 220, 0, 2))

LIMIT
  10