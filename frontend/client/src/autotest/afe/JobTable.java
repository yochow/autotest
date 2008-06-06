package autotest.afe;

import autotest.common.table.DataSource;
import autotest.common.table.DynamicTable;
import autotest.common.table.RpcDataSource;

import com.google.gwt.json.client.JSONObject;
import com.google.gwt.json.client.JSONString;
import com.google.gwt.json.client.JSONValue;

/**
 * A table to display jobs, including a summary of host queue entries.
 */
public class JobTable extends DynamicTable {
    public static final String HOSTS_SUMMARY = "hosts_summary";
    public static final String CREATED_TEXT = "created_text";

    public static final String[][] JOB_COLUMNS = { { "id", "ID" },
            { "owner", "Owner" }, { "name", "Name" },
            { "priority", "Priority" }, { "control_type", "Client/Server" },
            { CREATED_TEXT, "Created" }, { HOSTS_SUMMARY, "Status" } };

    public JobTable() {
        super(JOB_COLUMNS, new RpcDataSource("get_jobs_summary", 
                                             "get_num_jobs"));
        sortOnColumn("ID", DataSource.DESCENDING);
    }

    protected void preprocessRow(JSONObject row) {
        JSONObject counts = row.get("status_counts").isObject();
        String countString = AfeUtils.formatStatusCounts(counts, "<br>");
        row.put(HOSTS_SUMMARY, new JSONString(countString));
        
        // remove seconds from created time
        JSONValue createdValue = row.get("created_on");
        String created = "";
        if (createdValue.isNull() == null) {
            created = createdValue.isString().stringValue();
            created = created.substring(0, created.length() - 3);
        }
        row.put(CREATED_TEXT, new JSONString(created));
    }
}