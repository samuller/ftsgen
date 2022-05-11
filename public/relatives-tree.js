function familyMemberToTreantNode(member) {
    return {
        text: { name: `${member.firstName} ${member.lastName}` },
        link: { href: `#${member.personId}` },
        HTMLclass: member.gender == "M" ? "tree-male" : (
            member.gender == "F" ? "tree-female" : ""),
    };
}


function treeConfigRelatives(personId, husband, wife, children) {
    var nodes = [];
    nodes.push(familyMemberToTreantNode(husband));
    nodes.push({
        HTMLclass: "tree-rel-link",
        text: { name: "" },
        childrenDropLevel: 1,
        children: children.map((child) => {
            var newNode = familyMemberToTreantNode(child);
            if (child.personId == personId) {
                newNode.HTMLclass = "tree-main-person";
            }
            return newNode;
        })
    });
    nodes.push(familyMemberToTreantNode(wife));

    const chart_config = {
        chart: {
            container: "#parent-tree",
            rootOrientation: "WEST",
            connectors: {
                type: "step"
            },
            hideRootNode: true,
            node: {
                HTMLclass: "tree-dark-box"
            }
        },
        nodeStructure: {
            text: { name: "root" },
            children: nodes,
        }
    };
    return chart_config;
}


function treeRelatives(personId, relativeData) {
    // ignore other parent families (e.g. later adoptions, etc.)
    var mainFamily = relativeData.ischild[0];
    const husband = mainFamily.members.find(el => el.roleType == "husband");
    const children = mainFamily.members.filter(el => el.roleType.endsWith("child"));
    const wife = mainFamily.members.find(el => el.roleType == "wife");
    const chart_config = treeConfigRelatives(personId, husband, wife, children);
    return [chart_config, children.length];
}
