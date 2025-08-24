# fraudit/jobs/elt/loader.py
from fraudit.utils.logging import get_logger

logger = get_logger()

def write_to_postgres(df, jdbc_url, properties, checkpoint_path):
    def write_batch(batch_df, epoch_id):
        row_count = batch_df.count()
        logger.info(f"[Epoch {epoch_id}] Writing batch of {row_count} rows to PostgreSQL")
        batch_df.write.jdbc(
            url=jdbc_url,
            table="fraud_predictions",
            mode="append",
            properties=properties
        )

    return (
        df.writeStream 
        .outputMode("append")
        .trigger(processingTime="10 seconds")
        .option("checkpointLocation", checkpoint_path)
        .foreachBatch(write_batch)
        .start()
    )



