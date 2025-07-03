# fraudit/jobs/elt/loader.py

def write_to_postgres(df, jdbc_url, properties, checkpoint_path):
    return (
        df.writeStream 
        .outputMode("append")
        .trigger(processingTime="10 seconds")
        .option("checkpointLocation", checkpoint_path)
        .foreachBatch(lambda batch_df, epoch_id: batch_df.write
            .jdbc(url=jdbc_url, table="fraud_predictions", mode="append", properties=properties)
        )
        .start()
    )


