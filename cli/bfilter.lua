-- Written by Kirti Vardhan Rathore
-- based on the trivial protocol example provided at  https://wiki.wireshark.org/Lua/Dissectors#Examples
-- declare our protocol
bfilter_proto = Proto("bfilter","Binder Filter Protocol")
local f = bfilter_proto.fields
local formats = {"Binary", "Text", "Special"}

f.timestamp = ProtoField.uint32("bfilter.timestamp", "Uptime Timestamp")
f.type = ProtoField.string("bfilter.type", "Transaction Type")
f.euid = ProtoField.uint32("bfilter.euid", "Sender's effective user ID")
f.buffsize = ProtoField.uint32("bfilter.buffsize", "Size of the data buffer")
f.buff = ProtoField.bytes("bfilter.buff", "Data passed to the receiver")
f.offsize = ProtoField.uint32("bfilter.offsize","Size of the data at the given offset")
f.offdata = ProtoField.bytes("bfilter.offdata", "Data at the given offset")

-- create a function to dissect it
function bfilter_proto.dissector(buffer,pinfo,tree)
    pinfo.cols.protocol = "BinderFilter"
    local subtree = tree:add(bfilter_proto,buffer(),"Binder Filter Logs")
    local timestamp = buffer(0,4)
    subtree:add(f.timestamp,timestamp)
    local trtype = buffer(4,2):uint()

    if trype == 1 then
       subtree:add(f.type,"BC_TRANSACTION")
    else
       subtree:add(f.type,"BC_REPLY")
    end

    local euid = buffer(6,4)
    subtree:add(f.euid,euid)
    
    local buffsize = buffer(10,4):uint()
    subtree:add(f.buffsize,buffsize)

    local buff = buffer(14,buffsize)
    subtree:add(f.buff,buff)

    local offsize = buffer(14+buffsize,4):uint()
    subtree:add(f.offsize,offsize)

    local offdata = buffer(18+buffsize,offsize)
    subtree:add(f.offdata,offdata)
end

-- load the udp.port table
udp_table = DissectorTable.get("udp.port")
-- register our protocol to handle udp port 7777
udp_table:add(8085,bfilter_proto)
