from ripe.atlas.cousteau import AtlasResultsRequest
import attr
import logging
from pprint import pprint as pp
import pyasn
import base64
import dnslib

asndb = pyasn.pyasn('ipasn.20170420.1200')

def get_asn(ip):
    try:
        return asndb.lookup(ip)
    except ValueError as ex:
        _LOGGER.error("%s", ex)

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

@attr.s
class ResolverInfo:
    ts = attr.ib()
    from_ip = attr.ib()
    from_probe = attr.ib()
    #from_asn = attr.ib()

    #source = attr.ib()
    internal_resolvers = attr.ib()
    external_resolvers = attr.ib()
    resolver_asn = attr.ib()
    resolver_net = attr.ib()

    def merge(self, y):
        self.external_resolvers = self.external_resolvers.union(y.external_resolvers)
        self.resolver_asn = self.resolver_asn.union(y.resolver_asn)
        self.internal_resolvers = self.internal_resolvers.union(y.internal_resolvers)

        return self


HOMEPROBE = "27635"

# *https: // atlas.ripe.net / measurements / 8310237 / (google 'whoami')
# *https: // atlas.ripe.net / measurements / 8310245 / (akamai 'whoami')

def get_resolver_info(probe_ids, measurement):
    kwargs = {
        "msm_id": measurement,
        # "start": datetime(2017, 4, 1),
        # "stop": datetime(2017, 4, 2),
        "probe_ids": probe_ids
    }
    is_success, results = AtlasResultsRequest(**kwargs).create()
    if not is_success:
        _LOGGER.error("Request failed: %s %s", probe_ids, measurement)

    final_info = None
    for res in results:
        if "resultset" in res:
            res_set = res["resultset"]
            from_ip = res["from"]
            from_probe = res["prb_id"]

            for res_measure in res_set:
                if "result" not in res_measure:
                    _LOGGER.error("no results in measure: %s", res_measure)
                    continue
                dns_buf = dnslib.DNSRecord.parse(base64.b64decode(res_measure["result"]["abuf"]))

                int_resolver = res_measure["dst_addr"]
                if dns_buf.a.rdata is None:
                    _LOGGER.error("got no rdata")
                    continue
                ext_resolver = str(dns_buf.a.rdata).strip('"')
                x = get_asn(ext_resolver)
                if x is None:
                    asn = net = None
                else:
                    asn, net = x


                """
                <DNS RR: 'whoami.akamai.net.' rtype=A rclass=IN ttl=180 rdata='134.147.25.250'>
                <DNS RR: 'o-o.myaddr.l.google.com.' rtype=TXT rclass=IN ttl=60 rdata='"134.147.25.250"'>
                """

                info = ResolverInfo(ts=res["timestamp"],
                                    from_ip=from_ip,
                                    from_probe=from_probe,
                                    internal_resolvers=int_resolver,
                                    external_resolvers=ext_resolver,
                                    resolver_net=net,
                                    resolver_asn=asn)
                yield info

    #pp(results)

def get_info(probe):
    akamai = 8310245
    google = 8310237
    measurements = [akamai, google, 8310360, 8310360]
    #nlnet = get_resolver_info(probe)
    import itertools
    res = dict()
    for x in itertools.chain(*[get_resolver_info(probe, measure) for measure in measurements]):
        yield x
        #if x.from_probe in res:
        #    res[x.from_probe].merge(x)
        #else:
        #    res[x.from_probe] = x

    #return res

#q=[HOMEPROBE, 1,2,3,4]
q = None
for res in get_info(q):
    pp(attr.asdict(res))
