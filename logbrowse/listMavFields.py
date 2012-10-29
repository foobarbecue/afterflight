"""
List all mav message fields
"""
while True:
    m=mlog.recv_msg().to_dict()
    mptype=m['mavpackettype']
    if mptype not in typelist:
        typeList.append(mptype)
        for msgDatumType in m.keys():
            datumTypeList.append(msgDatumType)
