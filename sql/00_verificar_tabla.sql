-- Verificación de solo lectura para Supabase SQL Editor.
select
  count(*) as total_registros,
  count(distinct codigo_peaje) as total_peajes,
  min(anio) as anio_inicial,
  max(anio) as anio_final
from public.flujo_vehicular;
